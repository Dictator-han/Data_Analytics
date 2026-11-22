# Mac mini Wake-on-LAN（群晖版）

在家里与 Mac mini 同一局域网的 **群晖 NAS** 上部署一个极简唤醒服务：

- 命令行发送魔法包（`wake.py`）
- 带令牌保护的 HTTP API + 手机可打开的一键页面（`server.py`）
- Synology **Container Manager** 一键部署（`docker-compose.yml`）

## 1. 先在 Mac mini 上打开网络唤醒

1. 尽量用 **有线网口**（比 Wi‑Fi 可靠得多）。
2. macOS：**系统设置 → 电池 / 节能**（不同版本名称略有差异）  
   打开类似选项：
   - **唤醒以供网络访问**
   - 或 **Wake for network access / Power Nap** 相关项
3. 记下有线网卡 MAC：
   - **系统设置 → 网络 → 以太网 → 详细信息 → 硬件**
   - 或终端：`ifconfig en0 | grep ether`（有线常见为 `en0`/`en1`）

> 完全断电（拔掉电源）后，多数 Mac mini 无法被 WoL 唤醒；睡眠 / 关机（仍接电）才支持。

## 2. 拷到群晖

任选一种：

- File Station 上传整个 `mac-mini-wake` 目录，例如放到：  
  `/volume1/docker/mac-mini-wake`
- 或在群晖 SSH 里：

```sh
cd /volume1/docker
# 把本仓库同步/解压到 mac-mini-wake 后进入
cd mac-mini-wake
cp config.env.example config.env
```

编辑 `config.env`：

```env
DEVICE_NAME=Mac mini
MAC_ADDRESS=AA:BB:CC:DD:EE:FF
BROADCAST_ADDRESS=255.255.255.255
HTTP_PORT=8787
WAKE_TOKEN=请换成很长的随机串
```

生成令牌示例：

```sh
openssl rand -hex 24
```

若你的局域网是 `192.168.1.0/24`，更稳妥可写成：

```env
BROADCAST_ADDRESS=192.168.1.255
```

## 3. 用 Container Manager 安装（推荐）

### 方式 A：命令行（SSH）

确保已安装 **Container Manager**，然后：

```sh
cd /volume1/docker/mac-mini-wake
sudo docker compose up -d --build
sudo docker compose logs -f
```

默认使用 `network_mode: host`，UDP 广播才能打到局域网里的 Mac mini。

### 方式 B：图形界面

1. Container Manager → **项目** → **新增**
2. 路径选中本目录（含 `docker-compose.yml` 与 `config.env`）
3. 构建并启动

若群晖不允许 host 网络，改用：

```sh
sudo docker compose -f docker-compose.bridge.yml up -d --build
```

并务必把 `BROADCAST_ADDRESS` 设为网段定向广播（如 `192.168.1.255`）。

## 4. 怎么唤醒

### 浏览器（同一局域网 / 已做反向代理时）

打开：

```text
http://<群晖IP>:8787/
```

填入 `WAKE_TOKEN`，点「立即唤醒」。

### curl

```sh
curl -X POST \
  -H "Authorization: Bearer 你的WAKE_TOKEN" \
  -H "Content-Type: application/json" \
  http://<群晖IP>:8787/wake
```

### 群晖任务计划

1. 控制面板 → 任务计划 → 新增 → 用户定义的脚本  
2. 脚本内容可直接调用：

```sh
/bin/sh /volume1/docker/mac-mini-wake/scripts/synology-task.sh
```

或不用 Docker、只要有 `python3`：

```sh
/usr/bin/python3 /volume1/docker/mac-mini-wake/wake.py
```

### 本目录一键脚本

```sh
chmod +x scripts/*.sh
./scripts/wake.sh
```

## 5. 防火墙 / 外网访问（可选）

- 仅在家用：局域网访问 `8787` 即可，**不要**裸奔到公网。
- 需要外出唤醒时，优先：
  - 群晖 QuickConnect / VPN / Tailscale 进内网后再调 API  
  - 或在反向代理上加 HTTPS，并继续使用 `WAKE_TOKEN`
- 在 DSM 防火墙放行源地址受限的 `TCP 8787`（若启用了防火墙）。

## 6. 健康检查

```sh
curl http://<群晖IP>:8787/health
```

## 7. 排障

| 现象 | 排查 |
| --- | --- |
| API 返回成功但电脑不醒 | 确认 Mac 接电、节能项已开、MAC 是否为**当前网卡**（有线/无线不同） |
| Docker 已启动仍无效 | 是否用了 host 网络；bridge 模式下是否改成了 `192.168.x.255` |
| 401 Unauthorized | `WAKE_TOKEN` 与请求头不一致 |
| 端口打不开 | Container Manager 里容器是否 running；DSM 防火墙 |

本地快速自测魔法包封装（不依赖真机）：

```sh
python3 - <<'PY'
from wake import build_magic_packet, normalize_mac
pkt = build_magic_packet(normalize_mac("AA:BB:CC:DD:EE:FF"))
assert pkt.startswith(b"\xff"*6)
assert len(pkt) == 102
print("ok", len(pkt))
PY
```

## 目录说明

```text
mac-mini-wake/
├── wake.py                 # 发送魔法包（可单独用）
├── server.py               # HTTP API + 网页
├── config.env.example      # 配置模板
├── Dockerfile
├── docker-compose.yml      # 推荐：host 网络
├── docker-compose.bridge.yml
└── scripts/
    ├── wake.sh
    └── synology-task.sh
```

## 安全提醒

- `config.env` 含令牌与 MAC，**不要提交到公开仓库**（已在 `.gitignore`）。
- 定期更换 `WAKE_TOKEN`。
- 唤醒接口等价于「能开机」，权限按家里最敏感的服务来对待。
