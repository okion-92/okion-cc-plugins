# K8s / 容器 / Docker

> 由 sources/faq/ 生成，勿手改。每条 `## <slug>` 对应一个 source 文件，可在 ROUTING.md 反查。

## cluster-firewalld-port-whitelist — 集群版开启 firewalld 需放行的端口（含 k8s/istio 与 flannel 重置）


### 现象 / 场景
集群版各节点开启 firewalld 后，需按服务间访问关系放行端口，否则微服务/中间件/k8s/istio 互通失败。下例 IP 为脱敏拓扑，实际按本环境节点 IP 替换。

典型角色与服务：
- 负载与转发：nginx（443 对外）
- 微服务应用节点 ×N：明道云微服务（38880、8880）
- 中间件：Kafka(9092)/ZooKeeper/Elasticsearch(9200)/文件对象存储(9000)
- 数据存储：MySQL(3306)/MongoDB(27017)/Redis(6379)
- 数据集成：8081

### 处理

#### 通用命令
```bash
# ！！！添加策略后务必重载
firewall-cmd --reload
# 查看 public 下所有策略
firewall-cmd --zone=public --list-all
# 查看当前 zone
firewall-cmd --get-default-zone
# 添加/删除富规则（示例）
firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source address="<NGINX_IP>" port protocol="tcp" port="59100" accept'
firewall-cmd --permanent --zone=public --remove-rich-rule='rule family="ipv4" source address="<NGINX_IP>" port protocol="tcp" port="59100" accept'
# 端口策略
firewall-cmd --zone=public --add-port=443/tcp --permanent
firewall-cmd --zone=public --remove-port=443/tcp --permanent
```

#### 改动 firewalld 后 k8s 需重置网络（host-gw 模式下验证可行；ipip 模式把 flannel.1 改 flannel.ipip）
```bash
# 1、master 节点停止相关 k8s 服务
# 2、每个节点都要操作
systemctl stop kubelet
ifconfig cni0 down
ip link delete cni0
ifconfig flannel.1 down
ip link delete flannel.1
systemctl restart docker containerd kubelet
# 3、只在 master 节点操作
kubectl apply -f /usr/local/kubernetes/kube-flannel.yml
kubectl -n kube-system delete po $(kubectl -n kube-system get po|grep coredns|awk '{print $1}')
# 4、启动相关 k8s 服务
```
docker 环境改动 firewalld 后只需 `systemctl restart docker`。

#### 监控端口
```bash
# Node_exporter（每台都操作），源 IP 为采集端（如 nginx/监控机）
firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source address="<MONITOR_IP>" port protocol="tcp" port="59100" accept'
# Cadvisor（文件存储服务器）
firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source address="<MONITOR_IP>" port protocol="tcp" port="59101" accept'
# Prometheus
firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source address="<MONITOR_IP>" port protocol="tcp" port="9090" accept'
# Grafana
firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source address="<MONITOR_IP>" port protocol="tcp" port="3000" accept'
# kafka 监控
firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source address="<MONITOR_IP>" port protocol="tcp" port="59102" accept'
# k8s 监控
firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source address="<MONITOR_IP>" port protocol="tcp" port="6443" accept'
firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source address="<MONITOR_IP>" port protocol="tcp" port="30686" accept'
```

#### 服务间端口（对每个微服务节点 IP 各放行一条）
| 在哪台操作 | 端口 | 放行给 |
|---|---|---|
| 文件存储 | 9000 | 各微服务节点 + 数据集成 |
| Kafka | 9092 | 各微服务节点 + 数据集成 |
| Elasticsearch | 9200 | 各微服务节点 |
| MySQL | 3306 | 各微服务节点 |
| Redis | 6379 | 各微服务节点 |
| MongoDB | 27017 | 各微服务节点 |
| 数据集成 | 8081 | 各微服务节点 + 代理服务 |
| 微服务节点 | 38880 | 各微服务节点 |
| 代理服务 | 8880 | 微服务节点 |
| 代理服务 | 443 | 对外 |

```bash
# 示例：文件存储服务器对某微服务节点开放 9000
firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source address="<MS_NODE_IP>" port protocol="tcp" port="9000" accept'
```

#### k8s / istio 端口（用脚本批量管理）
> pod 之间网络不通时，额外放行 pod/service 网段：
> ```bash
> firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="10.96.0.0/12" accept'
> firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="10.244.0.0/16" accept'
> firewall-cmd --reload
> ```
> flannel vxlan 不行时改 ipip 或 host-gw（本环境 host-gw 成功）。

端口清单（脚本 `firewall-manager-ip.sh` 用法：`bash ./firewall-manager-ip.sh master|node|istio|remove-istio|remove-master|remove-node|list`）：
- K8S Master TCP：6443 2379 2380 10250 10259 10257 10256 10249 10248（源=所有 Node IP）
- K8S Node TCP：10250 10256 10249 10248（源=所有 Master IP）
- Istio TCP：443 10250 15017 15090 15053 15021 15020 15009 15008 15006 15004 15001 15000 15014 15012 15010
- Istio UDP：15053
- Istio 源：容器网段 10.244.0.0/16 + 集群所有节点 IP

```bash
#!/bin/bash
# touch firewall-manager-ip.sh && chmod +x firewall-manager-ip.sh
# bash ./firewall-manager-ip.sh master|node|istio|remove-istio|remove-master|remove-node|list
ZONE=public
TPC_N=tcp
UDP_N=udp
K8S_M_PORT_TCP_LIST=(6443 2379 2380 10250 10259 10257 10256 10249 10248)
K8S_N_PORT_TCP_LIST=(10250 10256 10249 10248)
K8S_ISTIO_PORT_TCP_LIST=(443 10250 15017 15090 15053 15021 15020 15009 15008 15006 15004 15001 15000 15014 15012 15010)
K8S_ISTIO_PORT_UDP_LIST=(15053)
K8S_M_IP=<K8S_MASTER_IP>
K8S_N1_IP=<K8S_NODE1_IP>
K8S_N2_IP=<K8S_NODE2_IP>
K8S_N3_IP=<K8S_NODE3_IP>
K8S_NETWORK=10.244.0.0/16
K8S_POD1_NETWORK=10.96.0.0/12
K8S_POD2_NETWORK=10.244.0.0/16

function k8s_M_tpc_add(){
      for tcp_port in ${K8S_M_PORT_TCP_LIST[@]}; do
            firewall-cmd --permanent --zone=$ZONE --add-rich-rule="rule family=ipv4 source address=$K8S_N1_IP port protocol=$TPC_N port=$tcp_port accept"
            firewall-cmd --permanent --zone=$ZONE --add-rich-rule="rule family=ipv4 source address=$K8S_N2_IP port protocol=$TPC_N port=$tcp_port accept"
            firewall-cmd --permanent --zone=$ZONE --add-rich-rule="rule family=ipv4 source address=$K8S_N3_IP port protocol=$TPC_N port=$tcp_port accept"
      done
      firewall-cmd --permanent --add-rich-rule="rule family=ipv4 source address=$K8S_POD1_NETWORK accept"
      firewall-cmd --permanent --add-rich-rule="rule family=ipv4 source address=$K8S_POD2_NETWORK accept"
}
function k8s_M_tpc_remove(){
      for tcp_port in ${K8S_M_PORT_TCP_LIST[@]}; do
            firewall-cmd --permanent --zone=$ZONE --remove-rich-rule="rule family=ipv4 source address=$K8S_N1_IP port protocol=$TPC_N port=$tcp_port accept"
            firewall-cmd --permanent --zone=$ZONE --remove-rich-rule="rule family=ipv4 source address=$K8S_N2_IP port protocol=$TPC_N port=$tcp_port accept"
            firewall-cmd --permanent --zone=$ZONE --remove-rich-rule="rule family=ipv4 source address=$K8S_N3_IP port protocol=$TPC_N port=$tcp_port accept"
      done
      firewall-cmd --permanent --remove-rich-rule="rule family=ipv4 source address=$K8S_POD1_NETWORK accept"
      firewall-cmd --permanent --remove-rich-rule="rule family=ipv4 source address=$K8S_POD2_NETWORK accept"
}
function k8s_N_tcp_add(){
      for tcp_port in ${K8S_N_PORT_TCP_LIST[@]}; do
            firewall-cmd --permanent --zone=$ZONE --add-rich-rule="rule family=ipv4 source address=$K8S_M_IP port protocol=$TPC_N port=$tcp_port accept"
      done
      firewall-cmd --permanent --add-rich-rule="rule family=ipv4 source address=$K8S_POD1_NETWORK accept"
      firewall-cmd --permanent --add-rich-rule="rule family=ipv4 source address=$K8S_POD2_NETWORK accept"
}
function k8s_N_tcp_remove(){
      for tcp_port in ${K8S_N_PORT_TCP_LIST[@]}; do
            firewall-cmd --permanent --zone=$ZONE --remove-rich-rule="rule family=ipv4 source address=$K8S_M_IP port protocol=$TPC_N port=$tcp_port accept"
      done
      firewall-cmd --permanent --remove-rich-rule="rule family=ipv4 source address=$K8S_POD1_NETWORK accept"
      firewall-cmd --permanent --remove-rich-rule="rule family=ipv4 source address=$K8S_POD2_NETWORK accept"
}
function k8s_ISTIO_add(){
      for istio_port in ${K8S_ISTIO_PORT_TCP_LIST[@]}; do
            firewall-cmd --permanent --zone=$ZONE --add-rich-rule="rule family=ipv4 source address=$K8S_NETWORK port protocol=$TPC_N port=$istio_port accept"
      done
      for istio_port in ${K8S_ISTIO_PORT_UDP_LIST[@]}; do
            firewall-cmd --permanent --zone=$ZONE --add-rich-rule="rule family=ipv4 source address=$K8S_NETWORK port protocol=$UDP_N port=$istio_port accept"
      done
      for istio_port in ${K8S_ISTIO_PORT_TCP_LIST[@]}; do
            for ip in $K8S_M_IP $K8S_N1_IP $K8S_N2_IP $K8S_N3_IP; do
                  firewall-cmd --permanent --zone=$ZONE --add-rich-rule="rule family=ipv4 source address=$ip port protocol=$TPC_N port=$istio_port accept"
            done
      done
      for istio_port in ${K8S_ISTIO_PORT_UDP_LIST[@]}; do
            for ip in $K8S_M_IP $K8S_N1_IP $K8S_N2_IP $K8S_N3_IP; do
                  firewall-cmd --permanent --zone=$ZONE --add-rich-rule="rule family=ipv4 source address=$ip port protocol=$UDP_N port=$istio_port accept"
            done
      done
}
function k8s_ISTIO_remove(){
      for istio_port in ${K8S_ISTIO_PORT_TCP_LIST[@]}; do
            firewall-cmd --permanent --zone=$ZONE --remove-rich-rule="rule family=ipv4 source address=$K8S_NETWORK port protocol=$TPC_N port=$istio_port accept"
      done
      for istio_port in ${K8S_ISTIO_PORT_UDP_LIST[@]}; do
            firewall-cmd --permanent --zone=$ZONE --remove-rich-rule="rule family=ipv4 source address=$K8S_NETWORK port protocol=$UDP_N port=$istio_port accept"
      done
      for istio_port in ${K8S_ISTIO_PORT_TCP_LIST[@]}; do
            for ip in $K8S_M_IP $K8S_N1_IP $K8S_N2_IP $K8S_N3_IP; do
                  firewall-cmd --permanent --zone=$ZONE --remove-rich-rule="rule family=ipv4 source address=$ip port protocol=$TPC_N port=$istio_port accept"
            done
      done
      for istio_port in ${K8S_ISTIO_PORT_UDP_LIST[@]}; do
            for ip in $K8S_M_IP $K8S_N1_IP $K8S_N2_IP $K8S_N3_IP; do
                  firewall-cmd --permanent --zone=$ZONE --remove-rich-rule="rule family=ipv4 source address=$ip port protocol=$UDP_N port=$istio_port accept"
            done
      done
}
usage="input master|node|istio|remove-istio|remove-master|remove-node|list"
[[ ! $1 ]] && echo $usage || case $1 in
master)        k8s_M_tpc_add; firewall-cmd --reload;;
node)          k8s_N_tcp_add; firewall-cmd --reload;;
istio)         k8s_ISTIO_add; firewall-cmd --reload;;
remove-istio)  k8s_ISTIO_remove; firewall-cmd --reload;;
remove-master) k8s_M_tpc_remove; firewall-cmd --reload;;
remove-node)   k8s_N_tcp_remove; firewall-cmd --reload;;
list)          firewall-cmd --zone=public --list-all;;
*)             echo $usage
esac
```

### 核验
`firewall-cmd --reload` 后 `firewall-cmd --zone=public --list-all` 应列出新增富规则；各节点间 `telnet <目标IP> <端口>` 通；k8s pod 间互通正常、coredns 重建后解析正常。

## debian-install-containerd — Debian 11/12 安装 containerd（k8s 用）


### 场景
Debian 11/12 上为 k8s 安装并配置 containerd 运行时。

```bash
apt-get install -y curl gnupg2 software-properties-common apt-transport-https ca-certificates
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update && apt-get install -y containerd.io

# 配置
containerd config default | tee /etc/containerd/config.toml >/dev/null 2>&1
sed -i 's/SystemdCgroup \= false/SystemdCgroup \= true/g' /etc/containerd/config.toml
sed -i 's#bin_dir \= "/opt/cni/bin"#bin_dir \= "/usr/local/kubernetes/cni/bin"#' /etc/containerd/config.toml
sed -i 's#sandbox_image \= "registry.k8s.io/pause:3.6"#sandbox_image \= "127.0.0.1:5000/pause:3.8"#' /etc/containerd/config.toml
sed -i 's#root \= "/var/lib/containerd"#root \= "/data/containerd"#' /etc/containerd/config.toml
grep "SystemdCgroup\|bin_dir\|sandbox_image\|^root" /etc/containerd/config.toml
systemctl restart containerd && containerd -v

# 依赖
apt-get -y install socat conntrack
```

## docker-8880-ipv6-occupied — docker 启动报 [::] 8880 端口被占用


### 场景
docker 启动报 [::]:8880 端口被占用（IPv6 监听冲突）。

`[::]` 是 IPv6 监听。禁用 IPv6 即可：
```bash
ip -6 addr show
# /etc/sysctl.conf 新增
net.ipv6.conf.all.disable_ipv6=1
sysctl -p   # 或 reboot
```

## docker-data-dir-migrate — Docker 数据目录迁移（/var/lib/docker 磁盘空间不足）


### 现象 / 场景
默认 Docker 存储目录 `/var/lib/docker` 所在分区（多为系统盘 `/`）空间不足，需把 Docker 数据目录迁移到更大的数据盘（如 `/data/docker`）。三种方式任选其一。每种方式都需先停服 + 停 docker + rsync 拷贝数据。

> 迁移验证完成前，**千万别删除** `/var/lib/docker-old`（或原 `/var/lib/docker`），确认镜像和容器正常运行后再删。

### 处理

公共第一步（三种方式都要先做）——停服、停 docker、拷贝数据：
```bash
# 停止明道云服务容器（管理器目录下）
bash service.sh stopall
# 停止 docker
systemctl stop docker
# 拷贝存储目录到目标盘（默认 /var/lib/docker → /data/，得到 /data/docker）
rsync -r -avz /var/lib/docker /data/
```

#### 方式 1：软链接
```bash
mv /var/lib/docker /var/lib/docker-old
ln -s /data/docker /var/lib/docker
# 重启验证
systemctl start docker
# 注意：一定要 restart 一下
systemctl restart docker
```

#### 方式 2：修改 ExecStart（推荐）
```bash
# 方式1(推荐)：修改 docker.service 中
#   ExecStart=/usr/bin/dockerd  →  ExecStart=/usr/bin/dockerd --graph=/data/docker

# 方式2：新建 drop-in 配置
mkdir -p /etc/systemd/system/docker.service.d/
cat > /etc/systemd/system/docker.service.d/devicemapper.conf << EOF
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd --graph=/data/docker
EOF

# 重启验证
systemctl daemon-reload
systemctl start docker
systemctl restart docker
```

#### 方式 3：mount --bind
```bash
mv /var/lib/docker /var/lib/docker-old
mkdir /var/lib/docker
# 查看 i 节点
ls -i /var/lib/ | grep docker && ls -i /data/docker/
mount --bind /data/docker /var/lib/docker
### 取消挂载：umount /var/lib/docker
# 检查 i 节点是否一致
ls -i /data/docker /var/lib/docker

# 开机自动挂载（注意原文件名应为 /etc/fstab）
cat >> /etc/fstab << EOF
/data/docker /var/lib/docker none bind 0 0
EOF

# 重启验证
systemctl start docker
systemctl restart docker
```

### 核验
```bash
docker info | grep "Docker Root Dir"
# 显示 Docker Root Dir: /data/docker 即迁移成功
```
镜像和容器能正常启动运行后，再删除 `/var/lib/docker-old`（或原 `/var/lib/docker`）回收空间。

## docker-mtu-network-unreachable — 网卡 MTU 低于 1500 导致 docker 网络不通无法通信


### 现象 / 场景
操作系统网卡 MTU 低于默认 1500（常见于云专线/隧道/VPC 环境），docker 默认网桥仍按 1500 封包，导致容器网络不通、无法通信。

### 原因
docker bridge 网络 MTU 默认 1500，大于宿主网卡实际 MTU 时大包被丢弃。

### 处理
查看宿主网卡实际 MTU（`ip addr` 看 `mtu` 值），在 docker-compose.yaml 中把 default 网络的 MTU 设为不超过该值（示例 1450，按实际网卡 MTU 填写）：

```yaml
networks:
  default:
    driver: bridge
    driver_opts:
      com.docker.network.driver.mtu: "1450"
```

改完重建容器（`docker compose down && docker compose up -d`）使新网络 MTU 生效。

### 核验
`docker network inspect <网络名>` 查看 `com.docker.network.driver.mtu` 为设定值；容器内 `ip addr` 网卡 MTU 已下调；跨主机/跨容器大包通信（如 `ping -s 1400 -M do <对端>`）正常，服务恢复互通。

## istio-ca-root-cert-not-found — istio 注入后 Pod 报 istio-ca-root-cert configmap not found


### 现象 / 场景
UOS Server 20 aarch64 部署 istio 后 Pod 无法启动，出现两类问题。

问题 1：istio-init 容器报 `iptables-restore: unable to initialize table 'nat'`，需加载 iptables 内核模块（详见 redhat8-istio-modules）：
```bash
lsmod | grep iptables
modprobe ip_tables
modprobe iptable_filter
modprobe iptable_nat
modprobe iptable_mangle
modprobe iptable_raw
```
开机自启加载：
```bash
cat > /etc/systemd/system/load-iptables-modules.service << EOF
[Unit]
Description=Load iptables modules
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/modprobe ip_tables
ExecStart=/sbin/modprobe iptable_filter
ExecStart=/sbin/modprobe iptable_nat
ExecStart=/sbin/modprobe iptable_mangle
ExecStart=/sbin/modprobe iptable_raw

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now load-iptables-modules
```
然后重新安装 istio。

问题 2（本篇重点）：Pod 报
```
MountVolume.SetUp failed for volume "istiod-ca-cert" : configmap "istio-ca-root-cert" not found
```

### 原因
istiod 启动时序问题，命名空间内 `istio-ca-root-cert` configmap 未被 istiod 写入/分发，导致挂载 `istiod-ca-cert` 卷失败。

### 处理
重启 istiod，让其重新生成并分发根证书 configmap：
```bash
kubectl rollout restart deployment istiod -n istio-system
```

参考：
- https://makeoptim.com/istio-faq/istio-ca-root-cert-not-found
- https://github.com/istio/istio/issues/22463

### 核验
`kubectl get configmap istio-ca-root-cert -A` 在各命名空间出现；之前因卷挂载失败的 Pod 重新调度后 Running，不再报 `istio-ca-root-cert not found`。

## istio-forward-proxy-serviceentry — 微服务启用正向代理时 istio 注意事项（ServiceEntry）


### 场景
启用 istio 后容器内走正向代理需加 ServiceEntry，否则经代理访问 HTTPS 返回 404（IP 变更时同步改）：
```bash
kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: ServiceEntry
metadata:
  name: proxy
spec:
  hosts:
  - my-company-proxy.com
  addresses:
  - <代理IP>/32
  ports:
  - number: <代理端口>
    name: tcp
    protocol: TCP
  location: MESH_EXTERNAL
EOF
```

## istio-plugin-deploy — istio 插件链路部署（镜像拉取/离线导入）


### 场景
要部署 istio 链路插件（监控 / kiali，在线拉取或离线导入镜像）。

在线拉取：
```bash
crictl pull registry.cn-hangzhou.aliyuncs.com/hap-mdy/all-in-one:1.35
crictl pull registry.cn-hangzhou.aliyuncs.com/hap-mdy/configmap-reload:v0.8.0
crictl pull registry.cn-hangzhou.aliyuncs.com/hap-mdy/prometheus:v2.41.0
crictl pull registry.cn-hangzhou.aliyuncs.com/hap-mdy/kiali:v1.67
```
离线导入（包见原记录附件）：
```bash
ctr -n k8s.io image import all-in-one-amd64-1.35.tar
ctr -n k8s.io image import configmap-reload-amd64-v0.8.0.tar
ctr -n k8s.io image import prometheus-amd64-v2.41.0.tar
ctr -n k8s.io image import kiali-amd64-v1.67.tar
```

## k8s-add-commandv2-service — K8s 集群新增 command v2（commandv2）微服务


### 现象 / 场景
集群版需为工作流相关服务接入新的 command v2（commandv2，node2011-python312）服务。需在 config.yaml 注入 4 个工作流扩展属性环境变量（指向 commandv2:9098），拉取镜像，在 service.yaml 追加 commandv2 的 Deployment + Service，再重启微服务。

### 处理

#### 1、config.yaml 新增环境变量（值不改动，base64 内容指向 commandv2:9098）
```yaml
# 挂载至容器内 /usr/local/MDPrivateDeployment/workflow/application-www-ext.properties
ENV_SERVICE_CONFIG_WORKFLOW_EXT_PROPERTIES: "L3Vzci9sb2NhbC9NRFByaXZhdGVEZXBsb3ltZW50L3dvcmtmbG93L2FwcGxpY2F0aW9uLXd3dy1leHQucHJvcGVydGllcw==:bWQuZ3JwYy5jbGllbnQuTURDb21tYW5kU2VydmljZVswXS5hZGRyZXNzPXN0YXRpYzovL2NvbW1hbmR2Mjo5MDk4Cm1kLmdycGMuY2xpZW50Lk1EQ29tbWFuZFNlcnZpY2VbMF0ubm9kZVZlcnNpb249MjAuMTEKbWQuZ3JwYy5jbGllbnQuTURDb21tYW5kU2VydmljZVswXS5weXRob25WZXJzaW9uPTMuMTI="

# 挂载至容器内 /usr/local/MDPrivateDeployment/workflowconsumer/application-www-ext.properties
ENV_SERVICE_CONFIG_WORKFLOWCONSUMER_EXT_PROPERTIES: "L3Vzci9sb2NhbC9NRFByaXZhdGVEZXBsb3ltZW50L3dvcmtmbG93Y29uc3VtZXIvYXBwbGljYXRpb24td3d3LWV4dC5wcm9wZXJ0aWVz:bWQuZ3JwYy5jbGllbnQuTURDb21tYW5kU2VydmljZVswXS5hZGRyZXNzPXN0YXRpYzovL2NvbW1hbmR2Mjo5MDk4Cm1kLmdycGMuY2xpZW50Lk1EQ29tbWFuZFNlcnZpY2VbMF0ubm9kZVZlcnNpb249MjAuMTEKbWQuZ3JwYy5jbGllbnQuTURDb21tYW5kU2VydmljZVswXS5weXRob25WZXJzaW9uPTMuMTI="

# 挂载至容器内 /usr/local/MDPrivateDeployment/workflowintegration/application-www-ext.properties
ENV_SERVICE_CONFIG_WORKFLOWINTEGRATION_EXT_PROPERTIES: "L3Vzci9sb2NhbC9NRFByaXZhdGVEZXBsb3ltZW50L3dvcmtmbG93aW50ZWdyYXRpb24vYXBwbGljYXRpb24td3d3LWV4dC5wcm9wZXJ0aWVz:bWQuZ3JwYy5jbGllbnQuTURDb21tYW5kU2VydmljZVswXS5hZGRyZXNzPXN0YXRpYzovL2NvbW1hbmR2Mjo5MDk4Cm1kLmdycGMuY2xpZW50Lk1EQ29tbWFuZFNlcnZpY2VbMF0ubm9kZVZlcnNpb249MjAuMTEKbWQuZ3JwYy5jbGllbnQuTURDb21tYW5kU2VydmljZVswXS5weXRob25WZXJzaW9uPTMuMTI="

# 挂载至容器内 /usr/local/MDPrivateDeployment/workflowplugin/application-www-ext.properties
ENV_SERVICE_CONFIG_WORKFLOWPLUGIN_EXT_PROPERTIES: "L3Vzci9sb2NhbC9NRFByaXZhdGVEZXBsb3ltZW50L3dvcmtmbG93cGx1Z2luL2FwcGxpY2F0aW9uLXd3dy1leHQucHJvcGVydGllcw==:bWQuZ3JwYy5jbGllbnQuTURDb21tYW5kU2VydmljZVswXS5hZGRyZXNzPXN0YXRpYzovL2NvbW1hbmR2Mjo5MDk4Cm1kLmdycGMuY2xpZW50Lk1EQ29tbWFuZFNlcnZpY2VbMF0ubm9kZVZlcnNpb249MjAuMTEKbWQuZ3JwYy5jbGllbnQuTURDb21tYW5kU2VydmljZVswXS5weXRob25WZXJzaW9uPTMuMTI="
```

#### 2、所有微服务节点都要拉取镜像
```bash
crictl pull registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-command:node2011-python312
```

#### 3、service.yaml 末尾新增 commandv2 服务（文件最后一空行添加）
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: commandv2
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: commandv2
  template:
    metadata:
      labels:
        app: commandv2
      annotations:
        md-update: "20230703103126"
    spec:
      containers:
      - name: commandv2
        image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-command:node2011-python312
        env:
        - name: ENV_SERVERID
          value: "single:command"
        resources:
          limits:
            cpu: "8"
            memory: 8192Mi
          requests:
            cpu: "0.01"
            memory: 64Mi
        readinessProbe:
          tcpSocket:
            port: 9098
          initialDelaySeconds: 10
          periodSeconds: 10
        livenessProbe:
          tcpSocket:
            port: 9098
          initialDelaySeconds: 180
          periodSeconds: 10


apiVersion: v1
kind: Service
metadata:
  name: commandv2
  namespace: default
spec:
  selector:
    app: commandv2
  ports:
    - name: grpc-commandv2
      port: 9098
      targetPort: 9098
```

#### 4、重启微服务

### 核验
`kubectl get pod | grep commandv2` 应 Running 且 9098 readiness 探针通过；工作流执行正常，workflow/workflowconsumer/workflowintegration/workflowplugin 能连到 commandv2:9098。

## k8s-batch-replace-replicas — K8s service.yaml 首次部署批量替换 Deployment 实例数


### 现象 / 场景
集群（精简版）首次部署时，需把 service.yaml 中一批微服务 Deployment/StatefulSet 的 `replicas` 按规划批量改写。手改易漏、易误，用脚本按 kind+name 精确定位替换，且内置「禁止缩容」保护（`ALLOW_SCALE_DOWN=false` 时旧值 > 目标值会跳过不动）。

> 说明：脚本按本环境实际实例规划设置 `SERVER_*_REPLICAS`，下例为精简版集群分组，按实际改。这是部署期批量改写工具，不是最低配置建议。

### 处理
```bash
cd /data/mingdao/script/kubernetes
touch replace_replicas.sh && chmod +x replace_replicas.sh
```

`replace_replicas.sh` 内容：
```bash
#!/bin/bash
set -euo pipefail

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FILE_N="service.yaml"

# 是否允许 replicas 从大改小（缩容）
# false = 不允许（默认，old > new 时跳过不修改，并提示）
# true  = 允许（old > new 时也会修改）
ALLOW_SCALE_DOWN=false

declare -a SERVER_1=(
    apitask alert calendaralert taskcenterdaily doc
)
SERVER_1_REPLICAS=1

declare -a SERVER_2=(
    command structure structureonlyworkflow worksheetexcelapi worksheetexcelapiconsumer 
    worksheetonlyworkflow worksheetconsumer wwwapiconsumer report worksheetonlyworkflowr
    workflowconsumer workflowrouterconsumer workflow worksheet api basiconlyworkflow wwwapi app
)
SERVER_2_REPLICAS=2

############################################
# Core helpers (safe, doc-bounded parsing)
############################################

# 读取：kind==KIND 且 metadata.name==NAME 的 spec.replicas
get_replicas_by_kind_and_name() {
  local file="$1"
  local kind="$2"   # Deployment / StatefulSet
  local name="$3"

  awk -v KIND="$kind" -v NAME="$name" '
  function reset_state() { is_kind=0; in_metadata=0; in_spec=0; name_ok=0; }
  BEGIN { reset_state(); }

  /^[[:space:]]*---[[:space:]]*$/ { reset_state(); next; }

  /^[[:space:]]*kind:[[:space:]]*/ {
    is_kind = ($0 ~ "^[[:space:]]*kind:[[:space:]]*"KIND"[[:space:]]*$") ? 1 : 0
  }

  /^[[:space:]]*metadata:[[:space:]]*$/ { in_metadata=1; in_spec=0; next; }
  /^[[:space:]]*spec:[[:space:]]*$/     { in_spec=1; in_metadata=0; next; }

  in_metadata && is_kind && $0 ~ "^[[:space:]]*name:[[:space:]]*"NAME"[[:space:]]*$" { name_ok=1 }

  in_spec && is_kind && name_ok && $0 ~ "^[[:space:]]*replicas:[[:space:]]*[0-9]+" {
    match($0, /[0-9]+/)
    print substr($0, RSTART, RLENGTH)
    exit
  }
  ' "$file"
}

# 修改：kind==KIND 且 metadata.name==NAME 的 spec.replicas（只改该文档内第一处 replicas）
set_replicas_by_kind_and_name() {
  local file="$1"
  local kind="$2"     # Deployment / StatefulSet
  local name="$3"
  local replicas="$4"

  awk -v KIND="$kind" -v NAME="$name" -v REPL="$replicas" '
  function reset_state() { is_kind=0; in_metadata=0; in_spec=0; name_ok=0; done=0; }
  BEGIN { reset_state(); }

  {
    # 文档边界：强制 reset，避免“越线”
    if ($0 ~ /^[[:space:]]*---[[:space:]]*$/) {
      print $0
      reset_state()
      next
    }

    # kind 判断
    if ($0 ~ /^[[:space:]]*kind:[[:space:]]*/) {
      is_kind = ($0 ~ "^[[:space:]]*kind:[[:space:]]*"KIND"[[:space:]]*$") ? 1 : 0
    }

    # 进入/退出 metadata/spec
    if ($0 ~ /^[[:space:]]*metadata:[[:space:]]*$/) { in_metadata=1; in_spec=0 }
    else if ($0 ~ /^[[:space:]]*spec:[[:space:]]*$/) { in_spec=1; in_metadata=0 }

    # 在 metadata 内识别 name
    if (in_metadata && is_kind && $0 ~ "^[[:space:]]*name:[[:space:]]*"NAME"[[:space:]]*$") {
      name_ok=1
    }

    # 只在目标对象的 spec 下替换第一处 replicas
    if (in_spec && is_kind && name_ok && !done && $0 ~ /^[[:space:]]*replicas:[[:space:]]*[0-9]+/) {
      sub(/[0-9]+[[:space:]]*$/, REPL)
      done=1
    }

    print $0
  }
  ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
}

############################################
# Public functions you call
############################################

deployment_replace_replicas() {
  local file="$1"
  local replicas_n="$2"
  shift 2

  for server in "$@"; do
    local old_replicas new_replicas
    old_replicas="$(get_replicas_by_kind_and_name "$file" "Deployment" "$server" || true)"
    echo -e "==[Before replacement]== replicas: ${old_replicas:-<not found>} --> deployment: $server"

    # 没找到 replicas：跳过并提示
    if [[ -z "${old_replicas:-}" ]]; then
      echo "!! [SKIP] replicas not found for Deployment/$server, no change."
      echo "============================================="
      continue
    fi

    # old > new 且不允许缩容：跳过并提示
    if (( old_replicas > replicas_n )) && [[ "$ALLOW_SCALE_DOWN" != "true" ]]; then
      echo "!! [SKIP] old replicas ($old_replicas) > target ($replicas_n). ALLOW_SCALE_DOWN=false, no change."
      echo "============================================="
      continue
    fi

    # old == new：跳过并提示（可选，但更清晰）
    if (( old_replicas == replicas_n )); then
      echo "== [NOOP] old replicas ($old_replicas) == target ($replicas_n). no change."
      echo "============================================="
      continue
    fi

    # 执行修改
    set_replicas_by_kind_and_name "$file" "Deployment" "$server" "$replicas_n"

    new_replicas="$(get_replicas_by_kind_and_name "$file" "Deployment" "$server" || true)"
    echo -e "==[After  replacement]== replicas: ${new_replicas:-<not found>} --> deployment: $server"
    echo "============================================="
  done

  echo "deployment Replacement completed."
  echo "============================================="
}

statefulset_replace_replicas() {
  local file="$1"
  local replicas_n="$2"
  shift 2

  for server in "$@"; do
    local old_replicas new_replicas
    old_replicas="$(get_replicas_by_kind_and_name "$file" "StatefulSet" "$server" || true)"
    echo -e "==[Before replacement]== replicas: ${old_replicas:-<not found>} --> statefulset: $server"

    if [[ -z "${old_replicas:-}" ]]; then
      echo "!! [SKIP] replicas not found for StatefulSet/$server, no change."
      echo "============================================="
      continue
    fi

    if (( old_replicas > replicas_n )) && [[ "$ALLOW_SCALE_DOWN" != "true" ]]; then
      echo "!! [SKIP] old replicas ($old_replicas) > target ($replicas_n). ALLOW_SCALE_DOWN=false, no change."
      echo "============================================="
      continue
    fi

    if (( old_replicas == replicas_n )); then
      echo "== [NOOP] old replicas ($old_replicas) == target ($replicas_n). no change."
      echo "============================================="
      continue
    fi

    set_replicas_by_kind_and_name "$file" "StatefulSet" "$server" "$replicas_n"

    new_replicas="$(get_replicas_by_kind_and_name "$file" "StatefulSet" "$server" || true)"
    echo -e "==[After  replacement]== replicas: ${new_replicas:-<not found>} --> statefulset: $server"
    echo "============================================="
  done

  echo "statefulset Replacement completed."
  echo "============================================="
}

############################################
# Main
############################################
main() {
  local target="$CURRENT_DIR/$FILE_N"

  # replace 2
  deployment_replace_replicas "$target" "$SERVER_2_REPLICAS" "${SERVER_2[@]}"

  # replace 1
  deployment_replace_replicas "$target" "$SERVER_1_REPLICAS" "${SERVER_1[@]}"

  # replace license (StatefulSet)
  statefulset_replace_replicas "$target" "2" "license"
}

main
```

执行：`./replace_replicas.sh`，每个服务打印 Before/After，找不到→SKIP，旧值==目标→NOOP，旧值>目标且禁缩容→SKIP。

### 核验
脚本输出中目标服务 `==[After replacement]== replicas: <目标值>`；`grep -A1 'name: <服务名>' service.yaml` 确认 replicas 已改；`kubectl apply -f service.yaml` 后 `kubectl get deploy` 实例数与规划一致。

## k8s-certs-auto-renew-cron — K8s 集群证书到期自动检查与续期脚本（cron）


### 场景
集群内 CA 证书默认一年有效期，需在到期前自动更新，避免证书过期引发异常。除手动 `kubeadm certs renew all`（另见 kubeadm-renew-long-term-certs）外，可在每个 Master 节点部署定时脚本自动检查并续期。

### 处理

手动检查与更新（任一节点到期前）：
```bash
# 检查证书何时过期
kubeadm certs check-expiration

# 在每个 Master 节点更新所有证书（执行后需重启控制面 Pod 才生效）
kubeadm certs renew all
```

#### 自动检查与续期（每个 Master 节点）

1. 各 Master 节点创建脚本目录：
```bash
mkdir /usr/local/kubernetes/script
```

2. `crontab -e` 写入定时任务（**各节点错开执行时间**，例如节点1凌晨1点、节点2凌晨2点、节点3凌晨3点）：
```cron
# Check and update kubernetes certificates regularly
0 1 * * * /bin/bash /usr/local/kubernetes/script/check_k8s_certs.sh
```

3. `vim /usr/local/kubernetes/script/check_k8s_certs.sh`，写入脚本：
```bash
#!/bin/bash

export KUBECONFIG=/etc/kubernetes/admin.conf
export PATH=/usr/local/kubernetes/bin/:$PATH

# 获取当前主机名（统一改为小写字母）
current_hostname=$(hostname | tr '[:upper:]' '[:lower:]')

# Kubernetes 证书目录
cert_dir="/etc/kubernetes/pki"

# 证书到期阈值
alert_days=7

# 日志函数
check_k8s_certs_log_file="/var/log/check_k8s_certs.log"
log_info() {
   echo "$(date +"%Y-%m-%d %H:%M:%S") INFO: $1" >> "$check_k8s_certs_log_file"
}

log_error() {
   echo "$(date +"%Y-%m-%d %H:%M:%S") ERROR: $1" >> "$check_k8s_certs_log_file"
}

# 当前日期
current_date=$(date +%s)

# 检查证书到期时间并更新
check_and_update_certs() {
   certs_to_update=()
   for cert in $(find $cert_dir -name "*.crt"); do

       # 获取证书的到期日期
       expiry_date=$(openssl x509 -enddate -noout -in $cert | cut -d= -f2)
       expiry_date_seconds=$(date -d "$expiry_date" +%s)

       # 计算剩余天数
       days_left=$((($expiry_date_seconds - $current_date) / 86400))

       # 如果证书到期阈值内，则加入更新列表
       if [ $days_left -le $alert_days ]; then
           certs_to_update+=("$cert")
       fi
   done

   if [ ${#certs_to_update[@]} -eq 0 ]; then
       log_info "Check completed, no certificates need to be updated."
   else
       for cert in "${certs_to_update[@]}"; do
           log_info "$cert certificate will expire within $alert_days days and needs to be updated."
       done

       # 更新证书并重启相关组件
       log_info "Start updating certificates"
       if kubeadm certs renew all >> "$check_k8s_certs_log_file"; then
           log_info "Certificate update successful."
           sleep 60s
           log_info "Start restarting control plane components"

           # 重启控制平面组件
           for pod_name in $(kubectl get pod -n kube-system | grep $current_hostname | grep "kube-apiserver\|kube-controller-manager\|kube-scheduler\|etcd" | awk '{print $1}'); do
               if kubectl -n kube-system delete pod $pod_name; then
                   log_info "Restart $pod_name successful."
                   sleep 60s
               else
                   log_error "Restart $pod_name failed."
               fi
           done
       else
           log_error "Certificate update failed."
       fi
   fi
}

main() {
   log_info "Start checking the expiration time of Kubernetes certificates"
   check_and_update_certs
}

main
```

### 核验
- `tail -f /var/log/check_k8s_certs.log` 看脚本执行日志（"no certificates need to be updated" 或更新/重启成功记录）。
- 续期后 `kubeadm certs check-expiration` 确认各证书过期时间已刷新；控制面 Pod 重建后 `kubectl get pod -n kube-system` 全部 Running。

## k8s-cli-tools-k9s-kubectl-completion — k8s 命令行工具：k9s 面板 + kubectl 补全


### 场景
想装 k9s 面板、开 kubectl tab 补全提升排障效率。

### k9s（命令行版 dashboard）
```bash
mkdir ~/mdtemp/k9s -p && cd ~/mdtemp/k9s
curl -OL https://github.com/derailed/k9s/releases/download/v0.26.7/k9s_Linux_x86_64.tar.gz
tar xzvf k9s_Linux_x86_64.tar.gz && ./k9s info
```
常用：`k9s --readonly`（只读）、`k9s -n kube-system`（指定 ns）；快捷键 ESC 上一级、`:q` 退出、enter 进 pod、d describe、l logs、n nodes。查 CPU/内存需部署 metrics-server。

### kubectl 补全（tab 补全）
```bash
apt-get install bash-completion -y     # centos: yum install bash-completion -y
source /usr/share/bash-completion/bash_completion
source <(kubectl completion bash)
echo "source /usr/share/bash-completion/bash_completion
source <(kubectl completion bash)" >> ~/.bashrc
```

## k8s-config-yaml-partial-restart — K8s 集群局部重启使 config.yaml 变量生效


### 场景
改了 config.yaml 变量后，需局部重启相关 Pod 让变量生效。

在 `config.yaml` 加了变量后（如外部门户微信登录的 4 个变量在 tpuser 生效），在服务运行状态下：
```bash
bash /data/mingdao/script/kubernetes/start.sh
kubectl get pods | grep config
kubectl delete pod <config-pod>      # 重建 config 使变量注入
kubectl get pods | grep config
kubectl delete pod <目标服务-pod>     # 如 tpuser，重建使其读到新变量
```
> 把目标服务换成实际读取该变量的服务（变量在哪个容器的 application-www.properties 生效就重建哪个）。

## k8s-coredns-forward-resolv — K8s CoreDNS forward /etc/resolv.conf 处理（钉钉集成失败相关）


### 场景
k8s 容器内 DNS 解析异常（钉钉集成失败相关），处理 CoreDNS forward 段。

检查 `/etc/resolv.conf` 中 DNS 解析是否可达、是否配置。**不可以注释** CoreDNS 里的 forward 段，否则钉钉集成会失败：
```
forward . /etc/resolv.conf {
   max_concurrent 1000
}
```
> 反之，若 coredns 因 `plugin/forward: no nameservers found` 起不来（resolv.conf 无可用 nameserver），才需 `kubectl edit cm coredns -n kube-system` 临时注释该段并重建 coredns pod——两种场景相反，按实际判断。

## k8s-flink-pod-install-nc — K8s 中给 Flink Pod 安装 nc（netcat）调试工具


### 现象 / 场景
排查 Flink 连通性（如数据管道 / SQLServer / Kafka 端口探测）时需要在 Flink Pod 内用 `nc`，但镜像未自带。通过 nerdctl 把 deb 包拷进容器安装。

### 处理

#### 1. 安装 nerdctl
```bash
wget http://pdpublic.mingdao.com/private-deployment/offline/common/kubernetes-1.25.4/nerdctl-1.7.0-linux-amd64.tar.gz
tar -zxvf nerdctl-1.7.0-linux-amd64.tar.gz
rm -f containerd-rootless*.sh
mv nerdctl /usr//bin/
cat >> ~/.bashrc <<EOF
alias nerdctl="nerdctl -n k8s.io"
EOF
source ~/.bashrc
```

#### 2. 下载 nc 及依赖 deb，拷进 Flink 容器并安装
```bash
wget http://archive.ubuntu.com/ubuntu/pool/main/n/netcat-openbsd/netcat-openbsd_1.218-4ubuntu1_amd64.deb
wget http://archive.ubuntu.com/ubuntu/pool/main/libb/libbsd/libbsd0_0.11.5-1_amd64.deb
wget http://archive.ubuntu.com/ubuntu/pool/main/libm/libmd/libmd0_1.0.4-1build1_amd64.deb

nerdctl ps |grep "registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-flink:1.17.1.530"

nerdctl cp netcat-openbsd_1.218-4ubuntu1_amd64.deb $(nerdctl ps |grep "registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-flink:1.17.1.530"|awk '{print $1}'):/opt/flink/
nerdctl cp libbsd0_0.11.5-1_amd64.deb $(nerdctl ps |grep "registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-flink:1.17.1.530"|awk '{print $1}'):/opt/flink/
nerdctl cp libmd0_1.0.4-1build1_amd64.deb $(nerdctl ps |grep "registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-flink:1.17.1.530"|awk '{print $1}'):/opt/flink/

nerdctl exec -it -u root $(nerdctl ps |grep "registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-flink:1.17.1.530"|awk 'NR==1{print $1}') bash

cd /opt/flink && dpkg -i *.deb
nc -h
```

#### 3.（可选）改用 apt 源在线安装
```bash
cp -p /etc/apt/sources.list /etc/apt/sources.list-bak$(date "+%Y%m%d%H%M")

cat > /etc/apt/sources.list << 'EOF'
deb https://mirrors.aliyun.com/ubuntu/ jammy main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ jammy main restricted universe multiverse

deb https://mirrors.aliyun.com/ubuntu/ jammy-security main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ jammy-security main restricted universe multiverse

deb https://mirrors.aliyun.com/ubuntu/ jammy-updates main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ jammy-updates main restricted universe multiverse

deb https://mirrors.aliyun.com/ubuntu/ jammy-backports main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ jammy-backports main restricted universe multiverse
EOF

apt update
```

### 核验
容器内 `nc -h` 正常输出，可用 `nc -zv <host> <port>` 探测目标连通性。

## k8s-mount-extension-code-deps — K8s 持久化挂载扩展代码依赖库（hostPath）


### 场景
要给 command 服务持久化挂载扩展代码依赖库（python/node，重启不丢）。

二进制文件/目录用 hostPath 挂载（不可输出内容的文件）。

### 文件挂载（如 sso）— service.yaml 对应 Deployment
```yaml
        volumeMounts:
        - mountPath: /usr/local/MDPrivateDeployment/sso/sso
          name: sso-volume
      volumes:
      - name: sso-volume
        hostPath:
          path: /data/mingdao/script/volume/sso/sso
          type: File
```

### 目录挂载（command 的 python/node 依赖库）
每节点先建目录并从 command pod 拷出现有依赖：
```bash
mkdir -p /data/mingdao/script/volume/command/package/python-3.6/site-packages
mkdir -p /data/mingdao/script/volume/command/package/nodejs-10.18.0/node_modules
kubectl cp $(kubectl get pod|grep command-|awk 'NR==1{print $1}'):/usr/local/lib/python3.6/site-packages /data/mingdao/script/volume/command/package/python-3.6/site-packages
kubectl cp $(kubectl get pod|grep command-|awk 'NR==1{print $1}'):/usr/local/node-10.18.0/lib/node_modules /data/mingdao/script/volume/command/package/nodejs-10.18.0/node_modules
```
service.yaml 的 command Deployment 加挂载（操作一次后重启生效）：
```yaml
        volumeMounts:
        - { mountPath: /usr/local/lib/python3.6/site-packages, name: python-volume }
        - { mountPath: /usr/local/node-10.18.0/lib/node_modules, name: node-volume }
      volumes:
      - name: python-volume
        hostPath: { path: /data/mingdao/script/volume/command/package/python-3.6/site-packages, type: Directory }
      - name: node-volume
        hostPath: { path: /data/mingdao/script/volume/command/package/nodejs-10.18.0/node_modules, type: Directory }
```

### 安装第三方库（多节点）
单节点安装后需同步到其余节点。安装示例：
```bash
# python
kubectl exec -it $(kubectl get pod|grep command-|awk 'NR==1{print $1}') -- /usr/local/bin/pip3 install --target=/usr/local/lib/python3.6/site-packages/ -i https://pypi.tuna.tsinghua.edu.cn/simple/ python-dateutil
# node
kubectl exec -it $(kubectl get pod|grep command-|awk 'NR==1{print $1}') -- /usr/local/node-10.18.0/bin/npm -g install dayjs
```
多节点同步（nc 传输 command 目录）：
```bash
# 接收节点：cd /data/mingdao/script/volume && nc -l 3838 | tar -zxvf -
# command 节点：cd /data/mingdao/script/volume && tar -zcvf - command/ | nc <目标节点IP> 3838
```
> 非 master 节点需 kubectl 权限：拷 `/etc/kubernetes/admin.conf` 到该节点并 `export KUBECONFIG=/etc/kubernetes/admin.conf`。
> 批量在每个 command 所在节点安装：`for pod in $(kubectl get pods -owide|grep command-|awk '!seen[$7]++'|awk '{print $1}'); do kubectl exec -it $pod -- /usr/local/bin/pip3 install --target=/usr/local/lib/python3.6/site-packages/ -i <镜像源> python-docx; done`

## k8s-reset-cleanup — K8s 集群 reset 重置并清理网络


### 场景
要 reset 重置 k8s 集群并清理残留网卡（cni0/flannel.1 网段不一致）。

```bash
kubeadm reset -f
# 清理网络（避免 cni0 与 flannel.1 网段不一致导致 pod 起不来报 cni0 错误）
ifconfig cni0 down;       ip link delete cni0
ifconfig flannel.1 down;  ip link delete flannel.1
```

### 核验
- `ip link show cni0` 与 `ip link show flannel.1` 均报 "does not exist"（残留网卡已删，避免网段不一致）。
- `kubeadm reset` 后重新 init/join 并部署 flannel，`kubectl get pod -A` 中网络相关 pod 起来为 Running、无 cni0 报错。

## k8s-temp-grpc-proxy-www — 集群专业版(K8s)临时修改 www 容器代理方式(gRPC 直连 basic)


### 适用场景
私有部署集群专业版(Kubernetes)，需临时修改 www 容器内的 Nginx 代理方式，把对 basic:5200 的 stream 代理改为 http2/grpc 代理（排查登录/gRPC 链路问题时使用）。

### 步骤
1、进入 www 容器（所有 www 容器都需修改，或先把 replicas 数量改成 1）
```
kubectl exec -it www-<pod-suffix> bash
```

2、创建日志目录
```
mkdir -p /data/logs/weblogs/
```

3、切换工作目录
```
cd /usr/local/nginx/conf/conf.d
```

4、修改 gateway.stream 文件中的配置（注释掉原 stream 段）
```
server {
    listen 5200;
    proxy_pass basic:5200;
}

修改为

# server {
#     listen 5200;
#     proxy_pass basic:5200;
# }
```

5、创建临时代理文件
```
cat > temp_basic.conf <<\EOF
upstream temp_basic{
    server basic:5200;
    keepalive 512;
}

server {
    listen 5200 http2;
    access_log /data/logs/weblogs/temp_basic.grpc.log main;
    error_log /data/logs/weblogs/temp_basic.grpc.error.log;
    location / {
        grpc_pass grpc://temp_basic;
    }
}
EOF
```

6、Nginx 配置检查
```
../../sbin/nginx  -t
# nginx: the configuration file /usr/local/nginx/conf/nginx.conf syntax is ok
# nginx: configuration file /usr/local/nginx/conf/nginx.conf test is successful
```

7、Nginx 配置重载
```
../../sbin/nginx -s reload
```

8、浏览器登录账号测试是否能正常登录

### 核验
查看 gRPC 日志文件出现日志输出即正常：
```
tail -n50  /data/logs/weblogs/temp_basic.grpc.log
```

## kernel-params-conn-reset — mongodb/redis/kafka 连接被 reset — 内核参数优化


### 场景
mongodb/redis/kafka 连接频繁被 reset，需调系统内核参数。

部分服务额外需要的内核参数（已存在的）：
```
# redis
net.core.somaxconn = 32768
# es
vm.max_map_count = 262144
vm.swappiness = 10
# k8s
vm.max_map_count = 262144
# istio
fs.inotify.max_user_watches = 10485760
fs.inotify.max_user_instances = 10240
```

所有 k8s 节点建议统一的 `/etc/sysctl.conf`（备份后覆盖，`sysctl -p` 生效）：
```
mv /etc/sysctl.conf /etc/sysctl.conf.backup-$(date +%Y%m%d%H%M%S)
cat > /etc/sysctl.conf <<EOF
kernel.msgmnb = 65536
kernel.msgmax = 65536
net.ipv6.conf.all.disable_ipv6 = 1
fs.file-max = 1000000
vm.swappiness = 10
fs.inotify.max_user_watches = 10000000
net.ipv4.neigh.default.gc_thresh1 = 2048
net.ipv4.neigh.default.gc_thresh2 = 4096
net.ipv4.neigh.default.gc_thresh3 = 8192
net.nf_conntrack_max = 524288
net.ipv4.tcp_max_tw_buckets = 5000
net.ipv4.tcp_max_syn_backlog = 32768
net.core.netdev_max_backlog = 32768
net.core.somaxconn = 32768
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 2
net.ipv4.ip_local_port_range = 1024 65000
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 10
net.ipv4.tcp_keepalive_probes = 3
vm.max_map_count = 262144
net.netfilter.nf_conntrack_tcp_timeout_established = 86400
fs.inotify.max_user_watches = 10485760
fs.inotify.max_user_instances = 10240
EOF
```
> 完整原文含更多 TCP 缓冲/conntrack 项；以上为关键集。

## kubeadm-config-init-k8s — kubeadm-config.yaml 方式初始化 k8s 集群（单/多 master）


### 场景
用 kubeadm-config.yaml 方式初始化 k8s 集群（单 / 多 master）。

### 单 master
```bash
kubeadm config print init-defaults > kubeadm-config.yaml
# 镜像仓库（本地 registry 示例）
sed -ri 's#imageRepository.*#imageRepository: 127.0.0.1:5000#' kubeadm-config.yaml
# podSubnet
sed -ri '/serviceSubnet/a \ \ podSubnet: 10.244.0.0\/16' kubeadm-config.yaml
# advertiseAddress 取本机内网 IP
sed -ri 's#advertiseAddress.*#advertiseAddress: '$(hostname -I |awk '{print $1}')'#' kubeadm-config.yaml
# etcd 数据目录
sed -ri 's#dataDir:.*#dataDir: /data/etcd#' kubeadm-config.yaml
# name 改为本机 hostname
sed -ri 's#name:.*#name: '$(hostname)'#' kubeadm-config.yaml
# 版本
sed -ri 's#kubernetesVersion.*#kubernetesVersion: 1.25.4#' kubeadm-config.yaml

kubeadm config images list --config kubeadm-config.yaml
kubeadm config images pull --config kubeadm-config.yaml
kubeadm init phase preflight --config=kubeadm-config.yaml
kubeadm init --config=kubeadm-config.yaml --upload-certs --v=6
```

### 多 master（额外加 controlPlaneEndpoint）
在单 master 基础上增加：
```bash
sed -i '/apiServer:/i controlPlaneEndpoint: "k8s-master:6443"' kubeadm-config.yaml
```
其余 images list/pull/preflight/init 同上。

## kubeadm-renew-long-term-certs — 更新 kubeadm 重新生成长期有效证书


### 场景
k8s 证书将过期 / 已过期，需续期并换长期有效证书。

检查与更新证书：
```bash
kubeadm certs check-expiration
kubeadm certs renew all
```

更新 kubeadm 二进制（用支持长期证书的版本）：
```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/kubernetes-1.25.4/kubeadm
chmod +x kubeadm
./kubeadm version | grep 'BuildDate:"2025-08-14T02:54:14Z"' | grep -v grep && echo -e "\e[32mdownload [ok]\e[0m" || echo -e "\e[31mdownload [error]\e[0m"
mv /usr/local/kubernetes/bin/kubeadm /usr/local/kubernetes/bin/kubeadm-bak$(date +%Y%m%d%H%M%S)
cp -p kubeadm /usr/local/kubernetes/bin/
kubeadm version | grep 'BuildDate:"2025-08-14T02:54:14Z"' | grep -v grep && echo -e "\e[32mupdate kubeadm [ok]\e[0m" || echo -e "\e[31mupdate kubeadm [error]\e[0m"
```

## redhat8-istio-modules — Redhat 8 部署 Istio 需加载内核模块


现象：Redhat 8 部署 Istio 后 Pod 报 `iptables-restore: unable to initialize table 'nat'`。加载模块：
```bash
cat > /etc/modules-load.d/istio.conf <<EOF
br_netfilter
nf_nat
xt_REDIRECT
xt_owner
iptable_nat
iptable_mangle
iptable_filter
EOF

modprobe br_netfilter nf_nat xt_REDIRECT xt_owner iptable_nat iptable_mangle iptable_filter
```

## swarm-cross-host-port-vxlan — Docker Swarm 容器跨主机端口不通(VXLAN 4789/8472)


### 现象
Docker Swarm 中，A 主机容器到 B 主机容器的端口不通。

### 原因 / 处理
宿主机 `4789/UDP` 为容器 overlay 入口端口（VXLAN），先检查此端口是否通畅。
若端口通，检查虚拟化网络层是否开启 VXLAN；冲突时改用 8472 端口重新初始化 Swarm：
- VMware NSX 6.2.3 之前默认 VXLAN 端口 8472
- VMware NSX 6.2.3 起新装默认 VXLAN 端口改为 4789

```bash
# 退出 Swarm 集群
docker swarm leave --force   # 管理节点
docker swarm leave           # 普通节点

# 用 8472 端口重新初始化
docker swarm init --data-path-port 8472
```

### 核验
重新组网后，跨主机容器端口互通。

## ubuntu-k8s-dns-resolve-fail — Ubuntu 上 K8s 容器内偶发域名解析失败


现象：宿主机解析正常，Pod 内偶发解析失败。

解决（两种方式，组合后问题消失）：
1. 改 CoreDNS 走 UDP：`kubectl -n kube-system edit configmap coredns`（按官方示例改 forward/协议为 udp）。改后解析失败率从 1% 降到约 1/14000。
2. 关闭 flannel 网卡 offload：
```bash
ethtool --offload flannel.1 rx off tx off
```
> 尚不确定哪种根治；先改 UDP 概率骤降，再补 ethtool 后不再复现。

## ubuntu22-containerd-online-cgroupv1 — Ubuntu 22.04 containerd 在线安装（解压包导致控制面 Pod 反复重启）+ cgroup v1 切换


### 现象 / 场景
Ubuntu 22.04.1 LTS (Jammy Jellyfish) 按解压包方式安装 containerd，k8s 初始化完成后 `kube-controller-manager` 和 `kube-scheduler` 这两个 Pod 会一直重启，导致服务不可用。改用在线安装（apt）可避免，且可指定版本。

### 处理

#### containerd 1.6.21 在线安装（ubuntu 22.04.1）
```bash
# 依赖
apt-get install -y curl gnupg2 software-properties-common apt-transport-https ca-certificates
# 安装源
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmour -o /etc/apt/trusted.gpg.d/docker.gpg
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
# 安装
apt update
# 可指定版本（需先查询可用版本）
apt install -y containerd.io
# 修改配置
containerd config default | sudo tee /etc/containerd/config.toml >/dev/null 2>&1
sed -i 's/SystemdCgroup =.*/SystemdCgroup = true/g' /etc/containerd/config.toml
sed -i 's#bin_dir =.*#bin_dir = "/usr/local/kubernetes/cni/bin"#' /etc/containerd/config.toml
sed -i 's#sandbox_image =.*#sandbox_image = "127.0.0.1:5000/pause:3.8"#' /etc/containerd/config.toml
sed -i 's#^root =.*#root = "/data/containerd"#' /etc/containerd/config.toml

# 检查
grep "SystemdCgroup\|bin_dir\|sandbox_image\|^root =" /etc/containerd/config.toml

# 重启
systemctl restart containerd
systemctl enable containerd

containerd -v
# 输出：containerd containerd.io 1.6.21
```

#### 检查 cgroup 版本
```bash
# 运行以下命令检查系统当前使用的 cgroup 版本：
stat -fc %T /sys/fs/cgroup/
# 如果输出为 cgroup2fs，则表示系统使用的是 cgroup v2。
# 如果输出为 tmpfs，则表示系统使用的是 cgroup v1。

# 此外，可以通过以下命令检查系统是否支持 cgroup v2：
grep cgroup /proc/filesystems
# 如果输出中包含 cgroup2，则表示系统支持 cgroup v2。
```

#### 修改为 cgroup v1
```bash
sed -i 's/SystemdCgroup =.*/SystemdCgroup = false/g' /etc/containerd/config.toml
grep SystemdCgroup /etc/containerd/config.toml

sed -i 's/cgroupDriver.*/cgroupDriver: cgroupfs/g' /var/lib/kubelet/config.yaml
grep cgroupDriver /var/lib/kubelet/config.yaml

systemctl restart containerd kubelet
```

### 核验
`containerd -v` 输出预期版本；k8s 初始化后 `kube-controller-manager`、`kube-scheduler` 不再反复重启，`kubectl get pod -n kube-system` 状态稳定为 Running。

