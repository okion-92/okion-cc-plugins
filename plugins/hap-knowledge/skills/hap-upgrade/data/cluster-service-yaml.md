---
title: HAP 集群新增微服务 service.yaml 完整配置（逐字核验，官方格式）
source_url: https://docs-pd.mingdao.com/deployment/kubernetes/upgrade/hap
last_verified: 2026-06-18   # 逐个 /upgrade/{ver}/ 原样核验
hap_version: any
tags: [upgrade, cluster, service-yaml]
feeds: [hap-upgrade]
---

集群 `/data/mingdao/script/kubernetes/service.yaml` 新增服务的**完整官方 YAML**（多行原格式，不压缩）。生成文档时**逐个原样铺，不要写"结构同上"、不要压缩成单行**。
- 所有微服务共用**同一目标镜像** `mingdaoyun-hap:{目标版本}`（下方块里写的是该版本，官方页显示的是引入版本号，因共用镜像故统一用目标版本）。
- requests 统一 `cpu: "0.01" / memory: 64Mi`；`md-update` 注解为官方原值，保留即可。

## templatemessage（4.4.0；3259 gRPC）
```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: templatemessage
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: templatemessage
  template:
    metadata:
      labels:
        app: templatemessage
      annotations:
        md-update: "20230610150218"
    spec:
      containers:
      - name: templatemessage
        image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:{目标版本}
        env:
        - name: ENV_SERVERID
          value: "single:templatemessage"
        resources:
          limits:
            cpu: "24"
            memory: 2048Mi
          requests:
            cpu: "0.01"
            memory: 64Mi
        readinessProbe:
          tcpSocket:
            port: 3259
          initialDelaySeconds: 10
          periodSeconds: 10
        livenessProbe:
          tcpSocket:
            port: 3259
          initialDelaySeconds: 180
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: templatemessage
  namespace: default
spec:
  selector:
    app: templatemessage
  ports:
    - name: grpc-templatemessage
      port: 3259
      targetPort: 3259
```

## wps（4.5.0；9017 http）
```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wps
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: wps
  template:
    metadata:
      labels:
        app: wps
      annotations:
        md-update: "20230831112233"
    spec:
      containers:
      - name: wps
        image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:{目标版本}
        env:
        - name: ENV_SERVERID
          value: "single:wps"
        resources:
          limits:
            cpu: "24"
            memory: 20480Mi
          requests:
            cpu: "0.01"
            memory: 64Mi
        readinessProbe:
          tcpSocket:
            port: 9017
          initialDelaySeconds: 10
          periodSeconds: 10
        livenessProbe:
          tcpSocket:
            port: 9017
          initialDelaySeconds: 180
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: wps
  namespace: default
spec:
  selector:
    app: wps
  ports:
    - name: http-wps
      port: 9017
      targetPort: 9017
```

## reportconsumer（5.0.0；消费者，无 Service，exec 探针）
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: reportconsumer
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: reportconsumer
  template:
    metadata:
      labels:
        app: reportconsumer
      annotations:
        md-update: "20230610150218"
    spec:
      containers:
      - name: reportconsumer
        image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:{目标版本}
        env:
        - name: ENV_SERVERID
          value: "single:reportconsumer"
        resources:
          limits:
            cpu: "24"
            memory: 20480Mi
          requests:
            cpu: "0.01"
            memory: 64Mi
        readinessProbe:
          exec:
            command: ["pgrep", "-f", "/usr/local/MDPrivateDeployment/reportconsumer/mdreport-consumer-1.0.0-SNAPSHOT.jar --spring.config.location=/usr/local/MDPrivateDeployment/reportconsumer/application-www.properties"]
          initialDelaySeconds: 10
          periodSeconds: 10
        livenessProbe:
          exec:
            command: ["pgrep", "-f", "/usr/local/MDPrivateDeployment/reportconsumer/mdreport-consumer-1.0.0-SNAPSHOT.jar --spring.config.location=/usr/local/MDPrivateDeployment/reportconsumer/application-www.properties"]
          initialDelaySeconds: 180
          periodSeconds: 10
```
> 官方仅给 Deployment，无 Service、无端口探针（用 exec pgrep 判存活）。

## computingschedule（5.1.0；9158 http + 9159 grpc）
```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: computingschedule
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: computingschedule
  template:
    metadata:
      labels:
        app: computingschedule
      annotations:
        md-update: "20240123163208"
    spec:
      containers:
      - name: computingschedule
        image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:{目标版本}
        env:
        - name: ENV_SERVERID
          value: "single:computingschedule"
        resources:
          limits:
            cpu: "24"
            memory: 2048Mi
          requests:
            cpu: "0.01"
            memory: 64Mi
        readinessProbe:
          tcpSocket:
            port: 9159
          initialDelaySeconds: 10
          periodSeconds: 10
        livenessProbe:
          tcpSocket:
            port: 9159
          initialDelaySeconds: 180
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: computingschedule
  namespace: default
spec:
  selector:
    app: computingschedule
  ports:
    - name: http-computingschedule
      port: 9158
      targetPort: 9158
    - name: grpc-computingschedule
      port: 9159
      targetPort: 9159
```
> 同版本还需把 `command` 服务镜像改为 `mingdaoyun-command:node1018-python36`（清持久化重装扩展）。

## commandpuppeteer（5.3.0；9198；readiness 30s）
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: commandpuppeteer
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: commandpuppeteer
  template:
    metadata:
      labels:
        app: commandpuppeteer
      annotations:
        md-update: "20240123163208"
    spec:
      containers:
      - name: commandpuppeteer
        image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:{目标版本}
        env:
        - name: ENV_SERVERID
          value: "single:commandpuppeteer"
        resources:
          limits:
            cpu: "24"
            memory: 20480Mi
          requests:
            cpu: "0.01"
            memory: 64Mi
        readinessProbe:
          tcpSocket:
            port: 9198
          initialDelaySeconds: 30
          periodSeconds: 10
        livenessProbe:
          tcpSocket:
            port: 9198
          initialDelaySeconds: 180
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: commandpuppeteer
  namespace: default
spec:
  selector:
    app: commandpuppeteer
  ports:
    - name: grpc-commandpuppeteer
      port: 9198
      targetPort: 9198
```

## datamanager（5.4.0；8322）
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: datamanager
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: datamanager
  template:
    metadata:
      labels:
        app: datamanager
      annotations:
        md-update: "20240123163208"
    spec:
      containers:
        - name: datamanager
          image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:{目标版本}
          env:
            - name: ENV_SERVERID
              value: "single:datamanager"
          resources:
            limits:
              cpu: "24"
              memory: 20480Mi
            requests:
              cpu: "0.01"
              memory: 64Mi
          readinessProbe:
            tcpSocket:
              port: 8322
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            tcpSocket:
              port: 8322
            initialDelaySeconds: 180
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: datamanager
  namespace: default
spec:
  selector:
    app: datamanager
  ports:
    - name: http-datamanager
      port: 8322
      targetPort: 8322
```
> 同版本 file 服务加环境变量 `ENV_FILE_DOMAIN: "http://file1:9000,http://file2:9000,http://file3:9000,http://file4:9000"`（与 `ENV_FILE_ENDPOINTS` 对齐、带 `http://`）。

## workflowplugin（5.8.0；8087 http + 9087 grpc）
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: workflowplugin
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: workflowplugin
  template:
    metadata:
      labels:
        app: workflowplugin
      annotations:
        md-update: "20240123163208"
    spec:
      containers:
      - name: workflowplugin
        image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:{目标版本}
        env:
        - name: ENV_SERVERID
          value: "single:workflowplugin"
        resources:
          limits:
            cpu: "24"
            memory: 20480Mi
          requests:
            cpu: "0.01"
            memory: 64Mi
        readinessProbe:
          tcpSocket:
            port: 8087
          initialDelaySeconds: 10
          periodSeconds: 10
        livenessProbe:
          tcpSocket:
            port: 8087
          initialDelaySeconds: 180
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: workflowplugin
  namespace: default
spec:
  selector:
    app: workflowplugin
  ports:
    - name: http-workflowplugin
      port: 8087
      targetPort: 8087
    - name: grpc-workflowplugin
      port: 9087
      targetPort: 9087
```
> 同版本给现有 `push` 服务的 Service `spec.ports` 增加：
```yaml
    - name: grpc-push
      port: 3009
      targetPort: 3009
```

## payment（6.2.0；9161 grpc）
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: payment
  template:
    metadata:
      labels:
        app: payment
      annotations:
        md-update: "20240123163208"
    spec:
      containers:
      - name: payment
        image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:{目标版本}
        env:
        - name: ENV_SERVERID
          value: "single:payment"
        resources:
          limits:
            cpu: "4"
            memory: 8096Mi
          requests:
            cpu: "0.01"
            memory: 64Mi
        readinessProbe:
          tcpSocket:
            port: 9161
          initialDelaySeconds: 10
          periodSeconds: 10
        livenessProbe:
          tcpSocket:
            port: 9161
          initialDelaySeconds: 180
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: payment
  namespace: default
spec:
  selector:
    app: payment
  ports:
    - name: grpc-payment
      port: 9161
      targetPort: 9161
```

## ai（7.0.0；8066 http）
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ai
  template:
    metadata:
      labels:
        app: ai
      annotations:
        md-update: "20240123163208"
    spec:
      containers:
      - name: ai
        image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:{目标版本}
        env:
        - name: ENV_SERVERID
          value: "single:ai"
        resources:
          limits:
            cpu: "4"
            memory: 8096Mi
          requests:
            cpu: "0.01"
            memory: 64Mi
        readinessProbe:
          tcpSocket:
            port: 8066
          initialDelaySeconds: 10
          periodSeconds: 10
        livenessProbe:
          tcpSocket:
            port: 8066
          initialDelaySeconds: 180
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: ai
  namespace: default
spec:
  selector:
    app: ai
  ports:
    - name: http-ai
      port: 8066
      targetPort: 8066
```

## mcp（7.0.0；8165 http）
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mcp
  template:
    metadata:
      labels:
        app: mcp
      annotations:
        md-update: "20240123163208"
    spec:
      containers:
      - name: mcp
        image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:{目标版本}
        env:
        - name: ENV_SERVERID
          value: "single:mcp"
        resources:
          limits:
            cpu: "4"
            memory: 8096Mi
          requests:
            cpu: "0.01"
            memory: 64Mi
        readinessProbe:
          tcpSocket:
            port: 8165
          initialDelaySeconds: 10
          periodSeconds: 10
        livenessProbe:
          tcpSocket:
            port: 8165
          initialDelaySeconds: 180
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: mcp
  namespace: default
spec:
  selector:
    app: mcp
  ports:
    - name: http-mcp
      port: 8165
      targetPort: 8165
```

## platformapi（7.3.0；1317）
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: platformapi
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: platformapi
  template:
    metadata:
      labels:
        app: platformapi
      annotations:
        md-update: "20240123163208"
    spec:
      containers:
      - name: platformapi
        image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:{目标版本}
        env:
        - name: ENV_SERVERID
          value: "single:platformapi"
        resources:
          limits:
            cpu: "4"
            memory: 8096Mi
          requests:
            cpu: "0.01"
            memory: 64Mi
        readinessProbe:
          tcpSocket:
            port: 1317
          initialDelaySeconds: 10
          periodSeconds: 10
        livenessProbe:
          tcpSocket:
            port: 1317
          initialDelaySeconds: 180
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: platformapi
  namespace: default
spec:
  selector:
    app: platformapi
  ports:
    - name: http-platformapi
      port: 1317
      targetPort: 1317
```

## openauthorization（7.3.0；5322）
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openauthorization
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: openauthorization
  template:
    metadata:
      labels:
        app: openauthorization
      annotations:
        md-update: "20240123163208"
    spec:
      containers:
      - name: openauthorization
        image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:{目标版本}
        env:
        - name: ENV_SERVERID
          value: "single:openauthorization"
        resources:
          limits:
            cpu: "4"
            memory: 8096Mi
          requests:
            cpu: "0.01"
            memory: 64Mi
        readinessProbe:
          tcpSocket:
            port: 5322
          initialDelaySeconds: 10
          periodSeconds: 10
        livenessProbe:
          tcpSocket:
            port: 5322
          initialDelaySeconds: 180
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: openauthorization
  namespace: default
spec:
  selector:
    app: openauthorization
  ports:
    - name: grpc-openauthorization
      port: 5322
      targetPort: 5322
```

## 7.3.0 删除 pushserver
从 `service.yaml` 删除 `pushserver` 的整段 Deployment 与 Service。
