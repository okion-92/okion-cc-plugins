import os
_HERE=os.path.dirname(os.path.abspath(__file__))
_SRC=os.path.join(_HERE,'deploy_src')
_OUT=os.environ.get('HAP_DEPLOY_WORK', os.path.join(_SRC,'_work'))
os.makedirs(_OUT, exist_ok=True)
# 按官方 monitor 页【逐字】重建监控章(仅参数化IP); 替换 deploy_tail.md 的 十二 章
import re

groups = [
 ("Nginx",       [("192.168.1.11","hap-nginx-01"),("192.168.1.12","hap-nginx-02")]),
 ("微服务/K8s",  [("192.168.1.2%d"%i,"hap-k8s-%02d"%i) for i in range(1,6)]),
 ("MySQL",       [("192.168.1.3%d"%i,"hap-mysql-%02d"%i) for i in range(1,4)]),
 ("MongoDB",     [("192.168.1.3%d"%(i+3),"hap-mongodb-%02d"%i) for i in range(1,4)]),
 ("Redis",       [("192.168.1.4%d"%i,"hap-redis-%02d"%i) for i in range(1,4)]),
 ("Kafka",       [("192.168.1.5%d"%i,"hap-kafka-%02d"%i) for i in range(1,4)]),
 ("Elasticsearch",[("192.168.1.6%d"%i,"hap-es-%02d"%i) for i in range(1,4)]),
 ("对象存储",    [("192.168.1.7%d"%i,"hap-storage-%02d"%i) for i in range(1,5)]),
 ("Flink",       [("192.168.1.8%d"%i,"hap-flink-%02d"%i) for i in range(1,4)]),
]
ne=[]
for label,nodes in groups:
    for ip,name in nodes:
        ne.append('      - targets: ["%s:59100"]'%ip)
        ne.append('        labels:')
        ne.append('          nodename: %s'%name)
        ne.append('          origin_prometheus: node')
NE="\n".join(ne)

MON = r'''# 十二、监控部署（Prometheus + Grafana）

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
@NE@

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

'''
def gen_ne(groups):
    ne=[]
    for label,nodes in groups:
        for ip,name in nodes:
            ne.append('      - targets: ["%s:59100"]'%ip)
            ne.append('        labels:'); ne.append('          nodename: %s'%name); ne.append('          origin_prometheus: node')
    return "\n".join(ne)

def build_monitor(ne, ndesc, cadvisor_ips, kafka_ip, k8s_ip, grafana_ip):
    cad="\n".join("        - %s:59101"%ip for ip in cadvisor_ips)
    m=MON
    m=m.replace("（所有节点均部署，:59100）", "（%s，:59100）"%ndesc)
    m=m.replace("@NE@", ne)
    m=m.replace('''      - targets:
        - 192.168.1.71:59101
        - 192.168.1.72:59101
        - 192.168.1.73:59101
        - 192.168.1.74:59101''', "      - targets:\n"+cad)
    m=m.replace("--kafka.server=192.168.1.51:9092","--kafka.server=%s:9092"%kafka_ip)
    m=m.replace('"192.168.1.51:59102"','"%s:59102"'%kafka_ip)
    m=m.replace("192.168.1.21:30686","%s:30686"%k8s_ip)
    m=m.replace("192.168.1.21:6443","%s:6443"%k8s_ip)
    m=m.replace("server 192.168.1.11:3000","server %s:3000"%grafana_ip)
    m=m.replace("server 192.168.1.11:9090","server %s:9090"%grafana_ip)
    return m

if __name__=='__main__':
    NE=gen_ne(groups)
    MONP=build_monitor(NE,"所有 29 个节点均部署",["192.168.1.71","192.168.1.72","192.168.1.73","192.168.1.74"],"192.168.1.51","192.168.1.21","192.168.1.11")
    tail = open(os.path.join(_SRC,'deploy_tail.md'),encoding='utf-8').read()
    pat = re.compile(r'# 十二、监控部署（Prometheus \+ Grafana）.*?(?=\n# 十三、上线验证与验收)', re.S)
    assert len(pat.findall(tail))==1, "monitor section match != 1"
    tail = pat.sub(MONP.rstrip(), tail)
    open(os.path.join(_SRC,'deploy_tail.md'),'w',encoding='utf-8').write(tail)
    print("monitor 章逐字重建; targets:", NE.count('- targets'),
          "| ClusterRole展开:", '  - configmaps' in MONP, "| 3×metric_relabel:", MONP.count('separator: ;')==3,
          "| 可选prometheus反代:", 'upstream prometheus' in MONP)
