# 七、Kubernetes 1.35.3 多 Master 集群（微服务节点 192.168.1.21-.25）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/kubernetes/kubernetes-1.35.3/multi-master-deployment
> 微服务层共 5 节点：3 Master（.21/.22/.23）+ 2 Worker（.24/.25）。

## 7.1 配置 hosts（所有 K8s 节点）

```bash
cat >> /etc/hosts <<EOF
192.168.1.21 k8s-master
192.168.1.22 k8s-master
192.168.1.23 k8s-master
EOF
```

> controlPlaneEndpoint 统一指向 k8s-master，由三 Master 共同承载。后续新增节点同样需要此 hosts。

## 7.2 安装 containerd 运行时（所有 K8s 节点）

```bash
cd 1.35-k8s-amd64-pkg
tar -zxvf containerd-static-2.2.2-linux-amd64.tar.gz
mv -f bin/* /usr/local/bin/
mkdir /etc/containerd
mv runc.amd64 /usr/local/bin/runc
chmod +x /usr/local/bin/runc

containerd config default > /etc/containerd/config.toml
sed -i \
  -e 's|SystemdCgroup =.*|SystemdCgroup = true|g' \
  -e 's|bin_dirs =.*|bin_dirs = ["/usr/local/kubernetes/cni/bin"]|' \
  -e 's|sandbox =.*|sandbox = "127.0.0.1:5000/pause:3.10.1"|' \
  -e 's|^root =.*|root = "/data/containerd"|' \
  /etc/containerd/config.toml

cat > /etc/systemd/system/containerd.service <<EOF
[Unit]
Description=containerd
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
ExecStart=/usr/local/bin/containerd --config /etc/containerd/config.toml
LimitNOFILE=1024000
LimitNPROC=infinity
LimitCORE=0
TimeoutStartSec=0
Delegate=yes
KillMode=process
Restart=on-failure
StartLimitBurst=3
StartLimitInterval=60s

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now containerd
```

## 7.3 安装 kubeadm/kubelet/kubectl（所有 K8s 节点）

```bash
mkdir -p /usr/local/kubernetes/bin
tar -zxvf crictl-v1.35.0-linux-amd64.tar.gz -C /usr/local/kubernetes/bin
\cp -rvf ./{kubeadm,kubelet,kubectl} /usr/local/kubernetes/bin/
chmod +x /usr/local/kubernetes/bin/*

cat > /etc/profile.d/kubernetes.sh <<'EOF'
export PATH=/usr/local/kubernetes/bin/:$PATH
EOF
source /etc/profile.d/kubernetes.sh
crictl config runtime-endpoint unix:///run/containerd/containerd.sock
```

> kubelet 的 systemd 单元与 10-kubeadm.conf 按官方文档写入后 `systemctl enable --now kubelet`。

## 7.4 生成 kubeadm 配置并初始化第一个 Master（192.168.1.21）

```bash
cd /usr/local/kubernetes/
kubeadm config print init-defaults > /usr/local/kubernetes/kubeadm-config.yaml
sed -ri 's|imageRepository.*|imageRepository: 127.0.0.1:5000|' kubeadm-config.yaml
sed -ri '/serviceSubnet/a \ \ podSubnet: 10.244.0.0\/16' kubeadm-config.yaml
sed -ri 's|advertiseAddress.*|advertiseAddress: '$(hostname -I |awk '{print $1}')'|' kubeadm-config.yaml
sed -ri 's|dataDir:.*|dataDir: /data/etcd|' kubeadm-config.yaml
sed -ri 's|name: node|name: '$(hostname)'|' kubeadm-config.yaml
sed -ri 's|kubernetesVersion.*|kubernetesVersion: 1.35.3|' kubeadm-config.yaml
sed -i '/apiServer:/i controlPlaneEndpoint: "k8s-master:6443"' kubeadm-config.yaml

kubeadm config images pull --config kubeadm-config.yaml
kubeadm init --config=kubeadm-config.yaml --upload-certs --v=6
```

## 7.5 Master 初始化后处理（每个 Master 执行）

```bash
sed -i '/- kube-apiserver/a\ \ \ \ - --service-node-port-range=1024-32767' /etc/kubernetes/manifests/kube-apiserver.yaml
echo 'export KUBECONFIG=/etc/kubernetes/admin.conf' >> /etc/profile.d/kubernetes.sh
source /etc/profile.d/kubernetes.sh
echo "maxPods: 300" >> /var/lib/kubelet/config.yaml
systemctl restart kubelet
# 允许 Master 调度业务 Pod（专业版微服务也跑在 Master 上）
kubectl taint node $(kubectl get node | grep control-plane | awk '{print $1}') node-role.kubernetes.io/control-plane:NoSchedule-
```

## 7.6 安装 Calico 网络（K8s 01 执行）

```bash
mv calico.yaml /usr/local/kubernetes/
sed -ri 's|image: quay.io/calico|image: 127.0.0.1:5000|g' /usr/local/kubernetes/calico.yaml
sed -i '/- name: cni-bin-dir/,/type:/s|path: .*|path: /usr/local/kubernetes/cni/bin|' /usr/local/kubernetes/calico.yaml
kubectl apply -f /usr/local/kubernetes/calico.yaml
kubectl get pod -n kube-system -l k8s-app=calico-node
```

## 7.7 其余 Master / Worker 加入集群

```bash
# Master 02 / 03（192.168.1.22 / .23）：用 kubeadm init 输出的 control-plane join 命令
kubeadm join k8s-master:6443 --token <TOKEN> \
  --discovery-token-ca-cert-hash sha256:<HASH> \
  --control-plane --certificate-key <KEY>
# 加入后重复 7.5 的后处理

# Worker 01 / 02（192.168.1.24 / .25）：
kubeadm join k8s-master:6443 --token <TOKEN> \
  --discovery-token-ca-cert-hash sha256:<HASH>
echo "maxPods: 300" >> /var/lib/kubelet/config.yaml
systemctl restart kubelet

# 如遗忘 join 命令，在 K8s 01 重新生成：
kubeadm token create --print-join-command
kubeadm init phase upload-certs --upload-certs
kubectl get node -o wide
```

# 八、Istio 1.29.1 安装

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/istio/istio-1.29.1/istio

```bash
# 调整 inotify 参数（所有 K8s 节点）
sysctl -w fs.inotify.max_user_watches=10485760
sysctl -w fs.inotify.max_user_instances=10240
cat >> /etc/sysctl.d/99-sysctl.conf <<EOF
fs.inotify.max_user_watches=10485760
fs.inotify.max_user_instances=10240
EOF

# 导入镜像（K8s 01）
gunzip -d kubeadm-1.35.3-images-amd64.tar.gz
ctr -n k8s.io image import kubeadm-1.35.3-images-amd64.tar

# 安装 Istio（K8s 01）
cd 1.35-k8s-amd64-pkg
tar -zxvf istio-1.29.1-linux-amd64.tar.gz -C /usr/local/
mv /usr/local/istio-1.29.1 /usr/local/istio
cat > /etc/profile.d/istio.sh <<'EOF'
export PATH=/usr/local/istio/bin/:$PATH
EOF
source /etc/profile.d/istio.sh
istioctl install --set profile=default -y --set values.global.hub=127.0.0.1:5000

# 为 default 命名空间开启自动注入
kubectl label namespace default istio-injection=enabled --overwrite
```

# 九、HAP 微服务部署（管理器在 K8s 01）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/service

## 9.1 部署管理器（Captain）

```bash
wget https://pdpublic.mingdao.com/private-deployment/7.3.4/mingdaoyun_private_deployment_captain_linux_amd64.tar.gz
mkdir /usr/local/MDPrivateDeployment/
tar -zxvf mingdaoyun_private_deployment_captain_linux_amd64.tar.gz -C /usr/local/MDPrivateDeployment/

cat > /etc/systemd/system/hap-manager.service <<'EOF'
[Unit]
Description=HAP Manager
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
WorkingDirectory=/usr/local/MDPrivateDeployment
ExecStart=/usr/bin/bash ./service.sh start
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now hap-manager
```

## 9.2 生成初始配置

```bash
cd /usr/local/MDPrivateDeployment/
bash ./service.sh install https://hap.domain.com
echo -n 'StageStart' > installer.stage
```

## 9.3 创建 ConfigMap（连接各集群）

以下为官方 env-list 完整变量集（Redis 哨兵模式用 SENTINEL 变量；IP/密码已参数化）：

```yaml
cat > config.yaml <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: env-list
  namespace: default
data:
  ENV_APP_VERSION: "7.3.4"
  ENV_MYSQL_HOST: "192.168.1.31"
  ENV_MYSQL_PORT: "6446"
  ENV_MYSQL_USERNAME: "root"
  ENV_MYSQL_PASSWORD: "<强密码>"
  ENV_MONGODB_URI: "mongodb://hap:<强密码>@192.168.1.34:27017,192.168.1.35:27017,192.168.1.36:27017"
  ENV_MONGODB_OPTIONS: "?replicaSet=local-mongodb-one&authSource=admin&maxIdleTimeMS=600000&maxLifeTimeMS=1800000"
  ENV_REDIS_SENTINEL_ENDPOINTS: "192.168.1.41:26379,192.168.1.42:26379,192.168.1.43:26379"
  ENV_REDIS_SENTINEL_MASTER: "mymaster"
  ENV_REDIS_SENTINEL_PASSWORD: "<强密码>"
  ENV_KAFKA_ENDPOINTS: "192.168.1.51:9092,192.168.1.52:9092,192.168.1.53:9092"
  ENV_ELASTICSEARCH_ENDPOINTS: "http://192.168.1.61:9200,http://192.168.1.62:9200,http://192.168.1.63:9200"
  ENV_ELASTICSEARCH_PASSWORD: "elastic:<强密码>"
  ENV_FILE_ENDPOINTS: "192.168.1.71:9001,192.168.1.72:9002,192.168.1.73:9003,192.168.1.74:9004"
  ENV_FILE_ACCESSKEY: "storage"
  ENV_FILE_SECRETKEY: "<强密码>"
  ENV_MINGDAO_INTRANET_ENDPOINT: "www:8880"
  ENV_ADDRESS_MAIN: "https://hap.domain.com"
  ENV_ADDRESS_ALLOWLIST: ""
  ENV_CAPTAIN_ENDPOINT: "http://192.168.1.21:38880"
  ENV_HEALTHCHECK: "off"
  ENV_API_TOKEN: "<高熵随机字符串>"
  ENV_TIME_ZONE: "Asia/Shanghai"
EOF
kubectl apply -f config.yaml
```

> ENV_MYSQL_HOST 填任一部署了 mysqlrouter 的 MySQL 节点（.31/.32/.33 均可），端口 6446 为 Router 读写口。
## 9.4 设置副本数并启动微服务

```bash
wget https://pdpublic.mingdao.com/private-deployment/data/set_microservice_replicas.sh
chmod +x set_microservice_replicas.sh
# 专业版用 professional 档位
bash set_microservice_replicas.sh professional

cd /data/mingdao/script/kubernetes/
bash start.sh
kubectl get pod -o wide
```

# 十、Flink 部署（数据同步节点 192.168.1.81 / .82 / .83）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/flink
> Flink 即 HDP 超级数据平台，承载聚合表 / 数据集成 / 超级数据平台计算。

## 10.1 导入镜像

```bash
gunzip -d mingdaoyun-flink-linux-amd64-1.19.720.tar.gz
ctr -n k8s.io image import mingdaoyun-flink-linux-amd64-1.19.720.tar
mkdir -p /data/mingdao/script/kubernetes/flink
cd /data/mingdao/script/kubernetes/flink
```

## 10.2 给 Flink 节点打污点 / 标签并创建命名空间

```bash
# 对 192.168.1.81 / .82 / .83 三个 Flink 节点执行（替换 $flink_node_name 为各节点名）
kubectl taint nodes $flink_node_name hap=flink:NoSchedule
kubectl label nodes $flink_node_name hap=flink
kubectl create ns flink
sed -i 's/namespace: default/namespace: flink/g' flink.yaml
```

## 10.3 flink-conf.yaml 关键项（对接 MinIO 与 Kafka）

```yaml
s3.access-key: mingdao
s3.secret-key: <强密码>
s3.ssl.enabled: false
s3.path.style.access: true
s3.endpoint: 192.168.1.71:9011
state.checkpoints.dir: s3://mdoc/checkpoints
state.savepoints.dir: s3://mdoc/savepoints
high-availability.storageDir: s3://mdoc/recovery
metrics.reporter.kafka_reporter.bootstrap.servers: 192.168.1.51:9092,192.168.1.52:9092,192.168.1.53:9092
jobmanager.memory.process.size: 3072m
taskmanager.memory.process.size: 12288m
```

> s3.endpoint 可指向任一 MinIO 节点端口（192.168.1.71:9011 / .72:9012 / .73:9013 / .74:9014 任选其一）；s3.access-key/secret-key 必须与 MinIO ROOT_USER/ROOT_PASSWORD 一致。

## 10.4 部署 Flink 并对接微服务

```bash
kubectl apply -f flink.yaml
kubectl get pod -n flink -o wide
# 在微服务 ConfigMap 追加（随后重启微服务生效）：
# ENV_FLINK_URL: "http://flink-jobmanager.flink:8081"
```

# 十一、Nginx + Keepalived 高可用（192.168.1.11 / .12，VIP 192.168.1.20）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/nginx/nginx-keepalived

## 11.1 hap.conf upstream（两台 Nginx 一致，指向 5 个微服务节点）

```bash
mkdir -p /data/logs/weblogs
cat > /usr/local/nginx/conf/hap.conf <<'EOF'
upstream hap {
    least_conn;
    server 192.168.1.21:8880 max_fails=3 fail_timeout=15s;
    server 192.168.1.22:8880 max_fails=3 fail_timeout=15s;
    server 192.168.1.23:8880 max_fails=3 fail_timeout=15s;
    server 192.168.1.24:8880 max_fails=3 fail_timeout=15s;
    server 192.168.1.25:8880 max_fails=3 fail_timeout=15s;
    keepalive 32;
}
server {
    listen 80;
    server_name hap.domain.com;
    access_log /data/logs/weblogs/hap.log;
    client_max_body_size 2048m;
    location / {
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $http_host;
        proxy_pass http://hap;
    }
}
EOF
```

## 11.2 keepalived.conf（Node01 priority 100 / Node02 priority 90）

```text
global_defs { router_id hap-nginx-ha-01 }
vrrp_script check_nginx_health {
    script "/usr/local/nginx/script/check_nginx_health.sh"
    interval 10
}
vrrp_instance VI_1 {
    state BACKUP
    interface eth0
    virtual_router_id 185
    priority 100          # Node02 改为 90
    advert_int 1
    nopreempt
    authentication { auth_type PASS; auth_pass HAP-Nginx-Keepalived-Auth }
    track_script { check_nginx_health }
    virtual_ipaddress { 192.168.1.20 }
}
```

## 11.3 健康检查脚本与启动（两台均执行）

```bash
mkdir -p /usr/local/nginx/script/
cat > /usr/local/nginx/script/check_nginx_health.sh <<'EOF'
#!/bin/bash
ps aux | grep nginx | grep -v grep | grep -v check_nginx_health
if [ $? -ne 0 ]; then
    systemctl stop keepalived
fi
EOF
chmod +x /usr/local/nginx/script/*.sh
systemctl enable --now nginx
systemctl enable --now keepalived
# 验证 VIP 漂移：在主节点 ip a 看到 192.168.1.20；停掉主 Nginx，VIP 应漂到备节点
```

# 十二、监控部署（Prometheus + Grafana）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/monitor/prometheus 、 .../monitor/grafana
> 以下配置与官方文档保持一致，仅 IP / 域名按本套拓扑参数化。

## 12.1 node_exporter（所有节点均部署，:59100）

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/node_exporter-1.9.1.linux-amd64.tar.gz
tar xf node_exporter-1.9.1.linux-amd64.tar.gz -C /usr/local/
mv /usr/local/node_exporter-1.9.1.linux-amd64 /usr/local/node_exporter
```

```ini
[Unit]
Description=Node Exporter for Prometheus
Documentation=https://github.com/prometheus/node_exporter
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/node_exporter/node_exporter --web.listen-address=:59100
User=root
Group=root
Restart=always
RestartSec=10
LimitNOFILE=102400

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable node_exporter
systemctl start node_exporter
```

## 12.2 cadvisor（仅运行 Docker 的节点，即对象存储 4 节点，:59101）

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/cadvisor-v0.52.1-linux-amd64
mkdir /usr/local/cadvisor
mv cadvisor-v0.52.1-linux-amd64 /usr/local/cadvisor/cadvisor
chmod +x /usr/local/cadvisor/cadvisor
```

```ini
[Unit]
Description=cAdvisor Container Monitoring
Documentation=https://github.com/google/cadvisor
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/cadvisor/cadvisor -port=59101
User=root
Group=root
Restart=always
RestartSec=10
LimitNOFILE=102400

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable cadvisor
systemctl start cadvisor
```

## 12.3 kafka_exporter（Kafka 集群任一节点，:59102；--kafka.server 改为实际 Kafka 地址）

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/kafka_exporter-1.9.0.linux-amd64.tar.gz
tar -zxvf kafka_exporter-1.9.0.linux-amd64.tar.gz -C /usr/local/
mv /usr/local/kafka_exporter-1.9.0.linux-amd64 /usr/local/kafka_exporter
```

```ini
[Unit]
Description=Kafka Exporter for Prometheus
Documentation=https://github.com/danielqsj/kafka_exporter
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/kafka_exporter/kafka_exporter --kafka.server=192.168.1.51:9092 --web.listen-address=:59102
User=root
Group=root
Restart=always
RestartSec=10
LimitNOFILE=102400

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable kafka_exporter
systemctl start kafka_exporter
```

## 12.4 kube-state-metrics（在 K8s 集群部署）

```bash
crictl pull registry.cn-hangzhou.aliyuncs.com/mdpublic/kube-state-metrics:2.3.0
mkdir -p /usr/local/kubernetes/ops-monit
cd /usr/local/kubernetes/ops-monit
```

ClusterRole：

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels:
    app.kubernetes.io/name: kube-state-metrics
    app.kubernetes.io/version: v2.3.0
  name: kube-state-metrics
rules:
- apiGroups:
  - ""
  resources:
  - configmaps
  - secrets
  - nodes
  - pods
  - services
  - resourcequotas
  - replicationcontrollers
  - limitranges
  - persistentvolumeclaims
  - persistentvolumes
  - namespaces
  - endpoints
  verbs:
  - list
  - watch
- apiGroups:
  - extensions
  resources:
  - daemonsets
  - deployments
  - replicasets
  - ingresses
  verbs:
  - list
  - watch
- apiGroups:
  - apps
  resources:
  - statefulsets
  - daemonsets
  - deployments
  - replicasets
  verbs:
  - list
  - watch
- apiGroups:
  - batch
  resources:
  - cronjobs
  - jobs
  verbs:
  - list
  - watch
- apiGroups:
  - autoscaling
  resources:
  - horizontalpodautoscalers
  verbs:
  - list
  - watch
- apiGroups:
  - authentication.k8s.io
  resources:
  - tokenreviews
  verbs:
  - create
- apiGroups:
  - authorization.k8s.io
  resources:
  - subjectaccessreviews
  verbs:
  - create
- apiGroups:
  - policy
  resources:
  - poddisruptionbudgets
  verbs:
  - list
  - watch
- apiGroups:
  - certificates.k8s.io
  resources:
  - certificatesigningrequests
  verbs:
  - list
  - watch
- apiGroups:
  - storage.k8s.io
  resources:
  - storageclasses
  - volumeattachments
  verbs:
  - list
  - watch
- apiGroups:
  - admissionregistration.k8s.io
  resources:
  - mutatingwebhookconfigurations
  - validatingwebhookconfigurations
  verbs:
  - list
  - watch
- apiGroups:
  - networking.k8s.io
  resources:
  - networkpolicies
  verbs:
  - list
  - watch
```

ClusterRoleBinding：

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  labels:
    app.kubernetes.io/name: kube-state-metrics
    app.kubernetes.io/version: v2.3.0
  name: kube-state-metrics
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kube-state-metrics
subjects:
- kind: ServiceAccount
  name: kube-state-metrics
  namespace: ops-monit
```

ServiceAccount：

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  labels:
    app.kubernetes.io/name: kube-state-metrics
    app.kubernetes.io/version: v2.3.0
  name: kube-state-metrics
  namespace: ops-monit
```

Deployment：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app.kubernetes.io/name: kube-state-metrics
    app.kubernetes.io/version: v2.3.0
  name: kube-state-metrics
  namespace: ops-monit
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: kube-state-metrics
  template:
    metadata:
      labels:
        app.kubernetes.io/name: kube-state-metrics
        app.kubernetes.io/version: v2.3.0
    spec:
      containers:
      - image: registry.cn-hangzhou.aliyuncs.com/mdpublic/kube-state-metrics:2.3.0
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 5
          timeoutSeconds: 5
        name: kube-state-metrics
        ports:
        - containerPort: 8080
          name: http-metrics
        - containerPort: 8081
          name: telemetry
        readinessProbe:
          httpGet:
            path: /
            port: 8081
          initialDelaySeconds: 5
          timeoutSeconds: 5
      nodeSelector:
        kubernetes.io/os: linux
      serviceAccountName: kube-state-metrics
```

Service：

```yaml
apiVersion: v1
kind: Service
metadata:
  labels:
    app.kubernetes.io/name: kube-state-metrics
    app.kubernetes.io/version: v2.3.0
  name: kube-state-metrics
  namespace: ops-monit
spec:
  ports:
  - name: http-metrics
    port: 8080
    targetPort: http-metrics
    nodePort: 30686
  - name: telemetry
    port: 8081
    targetPort: telemetry
  type: NodePort
  selector:
    app.kubernetes.io/name: kube-state-metrics
```

```bash
kubectl create namespace ops-monit
kubectl apply -f .
```

## 12.5 Prometheus 访问 K8s 的 RBAC（rbac.yaml）与 Token

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus
  namespace: kube-system
---
apiVersion: v1
kind: Secret
type: kubernetes.io/service-account-token
metadata:
  name: prometheus
  namespace: kube-system
  annotations:
    kubernetes.io/service-account.name: "prometheus"
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: prometheus
rules:
- apiGroups:
  - ""
  resources:
  - nodes
  - services
  - endpoints
  - pods
  - nodes/proxy
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - "extensions"
  resources:
    - ingresses
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - ""
  resources:
  - configmaps
  - nodes/metrics
  verbs:
  - get
- nonResourceURLs:
  - /metrics
  verbs:
  - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: prometheus
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: prometheus
subjects:
- kind: ServiceAccount
  name: prometheus
  namespace: kube-system
```

```bash
kubectl apply -f rbac.yaml
# 取 token 写入 Prometheus 节点
kubectl describe secret $(kubectl describe sa prometheus -n kube-system | sed -n '7p' | awk '{print $2}') -n kube-system | tail -n1 | awk '{print $2}'
# 将输出写入 /usr/local/prometheus/privatedeploy_kubernetes.token
```

## 12.6 Prometheus 安装与 prometheus.yml

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/prometheus-3.5.0.linux-amd64.tar.gz
tar -zxvf prometheus-3.5.0.linux-amd64.tar.gz -C /usr/local/
mv /usr/local/prometheus-3.5.0.linux-amd64 /usr/local/prometheus
```

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  # 服务器监控
  - job_name: "node_exporter"
    static_configs:
      - targets: ["192.168.1.11:59100"]
        labels:
          nodename: hap-nginx-01
          origin_prometheus: node
      - targets: ["192.168.1.12:59100"]
        labels:
          nodename: hap-nginx-02
          origin_prometheus: node
      - targets: ["192.168.1.21:59100"]
        labels:
          nodename: hap-k8s-01
          origin_prometheus: node
      - targets: ["192.168.1.22:59100"]
        labels:
          nodename: hap-k8s-02
          origin_prometheus: node
      - targets: ["192.168.1.23:59100"]
        labels:
          nodename: hap-k8s-03
          origin_prometheus: node
      - targets: ["192.168.1.24:59100"]
        labels:
          nodename: hap-k8s-04
          origin_prometheus: node
      - targets: ["192.168.1.25:59100"]
        labels:
          nodename: hap-k8s-05
          origin_prometheus: node
      - targets: ["192.168.1.31:59100"]
        labels:
          nodename: hap-mysql-01
          origin_prometheus: node
      - targets: ["192.168.1.32:59100"]
        labels:
          nodename: hap-mysql-02
          origin_prometheus: node
      - targets: ["192.168.1.33:59100"]
        labels:
          nodename: hap-mysql-03
          origin_prometheus: node
      - targets: ["192.168.1.34:59100"]
        labels:
          nodename: hap-mongodb-01
          origin_prometheus: node
      - targets: ["192.168.1.35:59100"]
        labels:
          nodename: hap-mongodb-02
          origin_prometheus: node
      - targets: ["192.168.1.36:59100"]
        labels:
          nodename: hap-mongodb-03
          origin_prometheus: node
      - targets: ["192.168.1.41:59100"]
        labels:
          nodename: hap-redis-01
          origin_prometheus: node
      - targets: ["192.168.1.42:59100"]
        labels:
          nodename: hap-redis-02
          origin_prometheus: node
      - targets: ["192.168.1.43:59100"]
        labels:
          nodename: hap-redis-03
          origin_prometheus: node
      - targets: ["192.168.1.51:59100"]
        labels:
          nodename: hap-kafka-01
          origin_prometheus: node
      - targets: ["192.168.1.52:59100"]
        labels:
          nodename: hap-kafka-02
          origin_prometheus: node
      - targets: ["192.168.1.53:59100"]
        labels:
          nodename: hap-kafka-03
          origin_prometheus: node
      - targets: ["192.168.1.61:59100"]
        labels:
          nodename: hap-es-01
          origin_prometheus: node
      - targets: ["192.168.1.62:59100"]
        labels:
          nodename: hap-es-02
          origin_prometheus: node
      - targets: ["192.168.1.63:59100"]
        labels:
          nodename: hap-es-03
          origin_prometheus: node
      - targets: ["192.168.1.71:59100"]
        labels:
          nodename: hap-storage-01
          origin_prometheus: node
      - targets: ["192.168.1.72:59100"]
        labels:
          nodename: hap-storage-02
          origin_prometheus: node
      - targets: ["192.168.1.73:59100"]
        labels:
          nodename: hap-storage-03
          origin_prometheus: node
      - targets: ["192.168.1.74:59100"]
        labels:
          nodename: hap-storage-04
          origin_prometheus: node
      - targets: ["192.168.1.81:59100"]
        labels:
          nodename: hap-flink-01
          origin_prometheus: node
      - targets: ["192.168.1.82:59100"]
        labels:
          nodename: hap-flink-02
          origin_prometheus: node
      - targets: ["192.168.1.83:59100"]
        labels:
          nodename: hap-flink-03
          origin_prometheus: node

  # docker 监控
  - job_name: "cadvisor"
    static_configs:
      - targets:
        - 192.168.1.71:59101
        - 192.168.1.72:59101
        - 192.168.1.73:59101
        - 192.168.1.74:59101

  # kafka 监控
  - job_name: kafka_exporter
    static_configs:
      - targets: ["192.168.1.51:59102"]

  # k8s 监控
  - job_name: privatedeploy_kubernetes_metrics
    static_configs:
      - targets: ["192.168.1.21:30686"] # 注意替换为 k8s 主节点地址
        labels:
          origin_prometheus: kubernetes

  - job_name: 'privatedeploy_kubernetes_cadvisor'
    scheme: https
    metrics_path: /metrics/cadvisor
    tls_config:
      insecure_skip_verify: true
    bearer_token_file: /usr/local/prometheus/privatedeploy_kubernetes.token
    kubernetes_sd_configs:
      - role: node
        api_server: https://192.168.1.21:6443 # 注意替换为 k8s 主节点地址
        bearer_token_file: /usr/local/prometheus/privatedeploy_kubernetes.token
        tls_config:
          insecure_skip_verify: true
    relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)
      - target_label: __address__
        replacement: 192.168.1.21:6443 # 注意替换为 k8s 主节点地址
      - target_label: origin_prometheus
        replacement: kubernetes
      - source_labels: [__meta_kubernetes_node_name]
        target_label: __metrics_path__
        replacement: /api/v1/nodes/${1}/proxy/metrics/cadvisor
    metric_relabel_configs:
      - source_labels: [instance]
        separator: ;
        regex: (.+)
        target_label: node
        replacement: $1
        action: replace
      - source_labels: [pod_name]
        separator: ;
        regex: (.+)
        target_label: pod
        replacement: $1
        action: replace
      - source_labels: [container_name]
        separator: ;
        regex: (.+)
        target_label: container
        replacement: $1
        action: replace
```

```ini
[Unit]
Description=Prometheus Monitoring System
Documentation=https://prometheus.io/docs/introduction/overview/
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/prometheus/prometheus \
  --storage.tsdb.path=/data/prometheus/data \
  --storage.tsdb.retention.time=30d \
  --config.file=/usr/local/prometheus/prometheus.yml \
  --web.enable-lifecycle
ExecReload=/usr/bin/curl -X POST http://127.0.0.1:9090/-/reload
User=root
Group=root
Restart=always
RestartSec=10
LimitNOFILE=102400

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable prometheus
systemctl start prometheus
# 配置变更后热加载：systemctl reload prometheus
```

## 12.7 Grafana 安装与配置

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/grafana_12.1.2_17957162798_linux_amd64.tar.gz
tar -xf grafana_12.1.2_17957162798_linux_amd64.tar.gz -C /usr/local/
mv /usr/local/grafana-12.1.2 /usr/local/grafana
```

```bash
sed -ri 's#^root_url = .*#root_url = %(protocol)s://%(domain)s:%(http_port)s/privatedeploy/mdy/monitor/grafana/#' /usr/local/grafana/conf/defaults.ini
sed -ri 's#^serve_from_sub_path = .*#serve_from_sub_path = true#' /usr/local/grafana/conf/defaults.ini
```

```ini
[Unit]
Description=Grafana Dashboard
Documentation=https://grafana.com/docs/
After=network.target

[Service]
Type=simple
WorkingDirectory=/usr/local/grafana
ExecStart=/usr/local/grafana/bin/grafana-server web
User=root
Group=root
Restart=always
RestartSec=10
LimitNOFILE=102400

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable grafana
systemctl start grafana
```

## 12.8 Nginx 反向代理 Grafana / Prometheus（追加到 hap.conf）

```text
upstream grafana {
    server 192.168.1.11:3000;
}

map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen      80;
    server_name  hap.domain.com;
    access_log /data/logs/weblogs/grafana.log main;
    error_log /data/logs/weblogs/grafana.mingdao.net.error.log;

    location /privatedeploy/mdy/monitor/grafana/ {
        proxy_hide_header X-Frame-Options;
        proxy_set_header X-Frame-Options ALLOWALL;
        proxy_set_header Host $http_host;
        proxy_pass http://grafana;
        proxy_redirect http://localhost:3000 http://hap.domain.com:80/privatedeploy/mdy/monitor/grafana;
    }

    location /privatedeploy/mdy/monitor/grafana/api/live {
        rewrite  ^/(.*)  /$1 break;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $http_host;
        proxy_pass http://grafana;
    }
}
```

可选：反向代理 Prometheus：

```text
upstream prometheus {
    server 192.168.1.11:9090;
}

location /privatedeploy/mdy/monitor/prometheus {
    rewrite ^/privatedeploy/mdy/monitor/prometheus$ / break;
    rewrite ^/privatedeploy/mdy/monitor/prometheus/(.*)$ /$1 break;
    proxy_pass http://prometheus;
    proxy_redirect /graph /privatedeploy/mdy/monitor/prometheus/graph;
}
```

> Grafana 初始账号/密码默认 admin/admin，首次登录强制修改为高强度密码。登录后 Connections → Data sources 添加 Prometheus 数据源（URL `http://127.0.0.1:9090`，保存前先 Validate），再导入官方 4 个 HAP 仪表盘 JSON（服务器资源 / Docker Swarm 容器 / Kafka 主题 / Kubernetes）。
# 十三、上线验证与验收

## 13.1 组件健康核验

| 组件 | 核验命令 / 方式 | 期望 |
| --- | --- | --- |
| MongoDB 副本集 | `rs.status()` | 1 Primary + 2 Secondary，无 unreachable |
| MySQL MGR | `SELECT * FROM performance_schema.replication_group_members;` | 3 行 ONLINE |
| MySQL Router | `mysql -h127.0.0.1 -P6446 -uroot -p` | 可写连接成功 |
| Redis 哨兵 | `redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster` | 返回当前 master |
| Kafka | `kafka-console-producer/consumer` 互通 | 收发正常 |
| Elasticsearch | `curl -u elastic:* :9200/_cat/health?v` | status green |
| MinIO | `docker stack ps minio` | 4 副本 Running |
| File | `docker stack ps file` | 4 副本 Running |
| K8s | `kubectl get node` / `kubectl get pod -A` | 全 Ready / Running |
| 微服务 | `kubectl get pod -o wide` | 全部 Running |
| Flink | `kubectl get pod -n flink` | JobManager/TaskManager Running |
| 入口 | 浏览器访问 https://hap.domain.com | 进入初始化向导 |

## 13.2 平台初始化与验收

1. 访问 https://hap.domain.com 完成超级管理员初始化（设置组织名、管理员账号密码）。
2. 新建一个测试应用 + 工作表，添加记录、上传附件并预览（验证 MinIO/File 链路）。
3. 配置一个简单工作流并触发（验证 Kafka + 工作流消费）。
4. 全文搜索一条记录（验证 Elasticsearch）。
5. 建一张聚合表 / 数据集成任务（验证 Flink/HDP）。
6. 停掉任一 MySQL/MongoDB/Redis 从节点，确认业务不中断（验证高可用）。
7. 核对监控面板（Grafana）各节点指标正常上报。

> 验收通过后，按《凭据登记表》登记所有真实密码并交客户妥善保管；按《运维文档》移交日常巡检、备份与故障处理流程。
