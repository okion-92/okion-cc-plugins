# 生成指定场景、指定4节点IP的 MinIO章 + File章 markdown(每节点完整展开)
import sys
scene=sys.argv[1]      # 'A' or 'B'
ips=sys.argv[2].split(',')   # 4个中间件节点IP
redis_ips=sys.argv[3].split(',')  # 3个Redis哨兵IP(标准/专业相同 .41/.42/.43)
out=sys.argv[4]

IMG_MINIO="registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-minio:RELEASE.2025-04-22T22-12-26Z"
IMG_FILE="registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-file:2.1.0"
minio_ports=[9011,9012,9013,9014]
file_ports=[9001,9002,9003,9004]
rds=redis_ips

def minio_chapter():
    L=[]
    L.append("# 九、中间件部署 — MinIO 集群（中间件节点 01/02/03/04）\n")
    if scene=='A':
        L.append("> 四节点 MinIO 部署（场景 A：未开启 Docker Swarm 集群）。4 台中间件节点（%s）之间 2377/4789 不通，每个节点各自运行一个**独立的单节点 Swarm**，互不编排；每节点部署本节点的 MinIO 服务。端口 9011-9014（容器内均 9000）。各节点需提前安装 Docker。" % " / ".join(ips))
    else:
        L.append("> 四节点 MinIO 纠删码集群（场景 B：开启 Docker Swarm 集群）。4 台中间件节点（%s）之间 2377/4789 互通，组成**同一个 Docker Swarm 集群**，由 Node01 作为 manager 统一编排。端口 9011-9014（容器内均 9000）。各节点需提前安装 Docker。" % " / ".join(ips))
    L.append("> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/minio/minio-cluster\n")

    # 9.1 Swarm
    if scene=='A':
        L.append("## 9.1 初始化单节点 Swarm（四节点各自执行）\n")
        L.append("> 场景 A 下每个节点各自初始化一个独立的单节点 Swarm，互不 join、无需记录 node.id，也不开放 2377 管理端口。\n")
        L.append("```text\n# 四个节点分别各自执行（互不 join）\ndocker swarm init\n```\n")
    else:
        L.append("## 9.1 初始化 Swarm 集群（Node01 init，其余 join）\n")
        L.append("> 场景 B 下 Node01 作为 manager 初始化，Node02/03/04 加入，组成同一 Swarm 集群。\n")
        L.append("""```text
# Node01 初始化（多 IP 时用 --advertise-addr 指定本机内网 IP）
docker swarm init --advertise-addr %s

# Node02/03/04 加入（token 由上一步输出，遗忘可在 Node01 执行 docker swarm join-token worker 查看）
docker swarm join --token xxxxxxxx %s:2377

# 在 Node01 记录各节点 ID（minio.yaml 的 placement 需要）
docker node ls
```\n""" % (ips[0], ips[0]))

    # 9.2 拉镜像建目录
    L.append("## 9.2 拉取镜像、建数据目录（四节点均执行）\n")
    L.append("```text\ndocker pull %s\nmkdir -p /usr/local/minio /data/minio/volume\n```\n" % IMG_MINIO)

    # 9.3 yaml
    if scene=='A':
        L.append("## 9.3 编写 minio.yaml（四节点，每节点一份单服务）\n")
        L.append("> 场景 A 下每个节点一份**只含本节点单个服务**的 minio.yaml，不含 deploy.placement。MINIO_ROOT_USER / PASSWORD 为示例，部署时改强口令。下面逐节点给出完整配置。\n")
        for idx,(ip,port) in enumerate(zip(ips,minio_ports),1):
            L.append("**MinIO Node%02d（%s）的 /usr/local/minio/minio.yaml：**\n"%(idx,ip))
            L.append("""```text
mkdir -p /usr/local/minio
cat > /usr/local/minio/minio.yaml <<'EOF'
version: '3'
services:
  minio%d:
    image: %s
    environment:
      MINIO_ROOT_USER: "mingdao"
      MINIO_ROOT_PASSWORD: "<强密码>"
    volumes:
      - /usr/share/zoneinfo/Etc/GMT-8:/etc/localtime
      - /data/minio/volume:/data/storage
    ports:
      - "%d:9000"
      # - "1911%d:9001" # console 端口，按需打开
    command: minio server http://minio{1...4}/data/storage/data --console-address ":9001"
EOF
```\n""" % (idx, IMG_MINIO, port, idx))
    else:
        L.append("## 9.3 编写 minio.yaml（仅 Node01，一份完整配置带 placement）\n")
        L.append("> 场景 B 下 4 个服务 minio1-4 放在同一份 minio.yaml，端口分别映射 9011-9014→9000，placement 按各节点 docker node.id 绑定。MINIO_ROOT_USER / PASSWORD 为示例，部署时改强口令。\n")
        svc=[]
        for idx,(ip,port) in enumerate(zip(ips,minio_ports),1):
            svc.append("""  minio%d:
    hostname: minio%d
    image: %s
    environment:
      MINIO_ROOT_USER: "mingdao"
      MINIO_ROOT_PASSWORD: "<强密码>"
    volumes:
      - /usr/share/zoneinfo/Etc/GMT-8:/etc/localtime
      - /data/minio/volume:/data/storage
    ports:
      - "%d:9000"
    command: minio server http://minio{1...4}/data/storage/data --console-address ":9001"
    deploy:
      placement:
        constraints:
          - node.id == <MinIO Node%02d（%s）的 node.id>""" % (idx,idx,IMG_MINIO,port,idx,ip))
        L.append("```text\nmkdir -p /usr/local/minio\ncat > /usr/local/minio/minio.yaml <<'EOF'\nversion: '3'\nservices:\n"+"\n".join(svc)+"\nEOF\n```\n")

    # 9.4 启停
    if scene=='A':
        L.append("## 9.4 启停脚本与启动（四节点各自执行）\n")
        L.append("> 场景 A 下每个节点分别创建启停脚本并分别启动。\n")
        L.append("""```text
cat > /usr/local/minio/start.sh <<'EOF'
docker stack deploy -c /usr/local/minio/minio.yaml minio --detach=false
EOF
cat > /usr/local/minio/stop.sh <<'EOF'
docker stack rm minio
EOF
chmod +x /usr/local/minio/start.sh /usr/local/minio/stop.sh

bash /usr/local/minio/start.sh
docker stack ps minio
```\n""")
    else:
        L.append("## 9.4 启停脚本与启动（仅 Node01）\n")
        L.append("> 场景 B 下仅 Node01 创建启停脚本并执行，Swarm 自动调度到 4 个节点。\n")
        L.append("""```text
cat > /usr/local/minio/start.sh <<'EOF'
docker stack deploy -c /usr/local/minio/minio.yaml minio --detach=false
EOF
cat > /usr/local/minio/stop.sh <<'EOF'
docker stack rm minio
EOF
chmod +x /usr/local/minio/start.sh /usr/local/minio/stop.sh

bash /usr/local/minio/start.sh
docker stack ps minio
```\n""")
    return "\n".join(L)

def file_chapter():
    L=[]
    L.append("# 十、中间件部署 — HAP 文件服务（中间件节点 01/02/03/04）\n")
    if scene=='A':
        L.append("> 四节点 File 服务（场景 A：未开启 Swarm，与 MinIO 共置 %s），镜像 mingdaoyun-file:2.1.0，端口 9001-9004（容器内 9000）。每节点各自运行本节点 file 服务，通过 s3-config.json 对接 MinIO。" % " / ".join(ips))
    else:
        L.append("> 四节点 File 服务（场景 B：开启 Swarm，与 MinIO 共置 %s），镜像 mingdaoyun-file:2.1.0，端口 9001-9004（容器内 9000），复用 MinIO 章节的同一 Swarm 集群，Node01 统一编排，通过 s3-config.json 对接 MinIO。" % " / ".join(ips))
    L.append("> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/file/v2/multi-node\n")

    # 10.1 拉镜像/目录/s3-config (四节点均执行；s3-config 各指向本机 MinIO)
    L.append("## 10.1 拉镜像、建目录、写 s3-config.json（四节点均执行，s3-config 各指向本机 MinIO）\n")
    L.append("> 集群中**每个节点都要写 s3-config.json**，且 bucketEndPoint 指向**本机**的 MinIO（IP 与端口逐节点不同：.x1→9011、.x2→9012、.x3→9013、.x4→9014）；accessKeyID/secretAccessKey 填 MinIO 的 ROOT_USER/ROOT_PASSWORD（四节点一致）；MinIO 用 IP 访问须设 addressingModel:1。下面逐节点给出完整内容。\n")
    L.append("**四节点通用前置（均执行）：**\n")
    L.append("""```text
docker pull %s
mkdir -p /data/file/volume/{cache,data,fetchtmp,multitmp,tmp}
mkdir -p /usr/local/MDPrivateDeployment/clusterMode/config
```\n""" % IMG_FILE)
    for idx,(ip,port) in enumerate(zip(ips,minio_ports),1):
        L.append("**File Node%02d（%s）的 s3-config.json（bucketEndPoint 指向本机 MinIO %s:%d）：**\n"%(idx,ip,ip,port))
        L.append("""```text
cat > /usr/local/MDPrivateDeployment/clusterMode/config/s3-config.json << EOF
{
  "mode": 1,
  "accessKeyID": "<MinIO ROOT_USER>",
  "secretAccessKey": "<MinIO ROOT_PASSWORD>",
  "bucketEndPoint": "http://%s:%d",
  "bucketName": {
    "mdmedia": "mdmedia",
    "mdpic": "mdpic",
    "mdpub": "mdpub",
    "mdoc": "mdoc"
  },
  "region": "1",
  "addressingModel": 1
}
EOF
```\n""" % (ip, port))

    domain='"'+",".join("http://%s:%d"%(ip,p) for ip,p in zip(ips,file_ports))+'"'
    sentinel='\n      ENV_REDIS_SENTINEL_ENDPOINTS: "%s:26379,%s:26379,%s:26379"\n      ENV_REDIS_SENTINEL_MASTER: "mymaster"\n      ENV_REDIS_SENTINEL_PASSWORD: "<强密码>"'%(rds[0],rds[1],rds[2])

    if scene=='A':
        L.append("## 10.2 编写 file.yaml（四节点，每节点一份单服务）\n")
        L.append("> 场景 A 下每节点一份**只含本节点单个 file 服务**的 file.yaml，不含 placement；每实例 ENV_FILE_ID 唯一、ENV_FILE_DOMAIN 填全部 4 节点。下面逐节点给出完整配置。\n")
        for idx,(ip,port) in enumerate(zip(ips,file_ports),1):
            L.append("**File Node%02d（%s）的 file.yaml：**\n"%(idx,ip))
            L.append("""```text
cat > /usr/local/MDPrivateDeployment/clusterMode/file.yaml <<EOF
version: '3'
services:
  file%d:
    hostname: file%d
    image: %s
    volumes:
      - /usr/share/zoneinfo/Etc/GMT-8:/etc/localtime
      - /data/file/volume:/data/storage
      - /usr/local/MDPrivateDeployment/clusterMode/config/s3-config.json:/usr/local/file/s3-config.json
    ports:
      - "%d:9000"
    environment:
      ENV_ACCESS_KEY_FILE: storage
      ENV_SECRET_KEY_FILE: <强密码>
      ENV_MINGDAO_PROTO: "http"
      ENV_MINGDAO_HOST: "hap.domain.com"
      ENV_MINGDAO_PORT: "80"%s
      ENV_FILECACHE_EXPIRE: "false"
      ENV_FILE_ID: "file%d"
      ENV_FILE_DOMAIN: %s
    command: ["./main", "server", "/data/storage/data"]
EOF
```\n""" % (idx,idx,IMG_FILE,port,sentinel,idx,domain))
    else:
        L.append("## 10.2 编写 file.yaml（仅 Node01，一份完整配置带 placement）\n")
        L.append("> 场景 B 下 4 个服务 file1-4 放在同一份 file.yaml，端口 9001-9004→9000，placement 按各节点 node.id 绑定（复用 9.x 查到的 node.id）；每实例 ENV_FILE_ID 唯一。\n")
        svc=[]
        for idx,(ip,port) in enumerate(zip(ips,file_ports),1):
            svc.append("""  file%d:
    hostname: file%d
    image: %s
    volumes:
      - /usr/share/zoneinfo/Etc/GMT-8:/etc/localtime
      - /data/file/volume:/data/storage
      - /usr/local/MDPrivateDeployment/clusterMode/config/s3-config.json:/usr/local/file/s3-config.json
    ports:
      - "%d:9000"
    environment:
      ENV_ACCESS_KEY_FILE: storage
      ENV_SECRET_KEY_FILE: <强密码>
      ENV_MINGDAO_PROTO: "http"
      ENV_MINGDAO_HOST: "hap.domain.com"
      ENV_MINGDAO_PORT: "80"%s
      ENV_FILECACHE_EXPIRE: "false"
      ENV_FILE_ID: "file%d"
      ENV_FILE_DOMAIN: %s
    command: ["./main", "server", "/data/storage/data"]
    deploy:
      placement:
        constraints:
          - node.id == <File Node%02d（%s）的 node.id>""" % (idx,idx,IMG_FILE,port,sentinel,idx,domain,idx,ip))
        L.append("```text\ncat > /usr/local/MDPrivateDeployment/clusterMode/file.yaml <<EOF\nversion: '3'\nservices:\n"+"\n".join(svc)+"\nEOF\n```\n")

    # 10.3 启停
    if scene=='A':
        L.append("## 10.3 启停脚本与启动（四节点各自执行）\n")
        L.append("""```text
cat > /usr/local/MDPrivateDeployment/clusterMode/start.sh <<EOF
docker stack deploy -c /usr/local/MDPrivateDeployment/clusterMode/file.yaml file --detach=false
EOF
cat > /usr/local/MDPrivateDeployment/clusterMode/stop.sh <<EOF
docker stack rm file
EOF
chmod +x /usr/local/MDPrivateDeployment/clusterMode/start.sh /usr/local/MDPrivateDeployment/clusterMode/stop.sh

bash /usr/local/MDPrivateDeployment/clusterMode/start.sh
docker stack ps file
```\n""")
    else:
        L.append("## 10.3 启停脚本与启动（仅 Node01）\n")
        L.append("""```text
cat > /usr/local/MDPrivateDeployment/clusterMode/start.sh <<EOF
docker stack deploy -c /usr/local/MDPrivateDeployment/clusterMode/file.yaml file --detach=false
EOF
cat > /usr/local/MDPrivateDeployment/clusterMode/stop.sh <<EOF
docker stack rm file
EOF
chmod +x /usr/local/MDPrivateDeployment/clusterMode/start.sh /usr/local/MDPrivateDeployment/clusterMode/stop.sh

bash /usr/local/MDPrivateDeployment/clusterMode/start.sh
docker stack ps file
```\n""")
    return "\n".join(L)

open(out,'w').write(minio_chapter()+"\n"+file_chapter()+"\n")
print("生成",out,"场景",scene)
