# OpenWrt 系统级热插拔兜底脚本 (Contrib Hotplug Scripts)

本目录下包含用于软路由系统的热插拔维护脚本。这些脚本**独立于 OpenClash 代码库与 GitHub Actions 打包流程**，专门部署在软路由系统的 `/etc/hotplug.d/` 目录下，用于解决 Linux 内核与网络变更引起的边界问题。

---

## 脚本清单

### 1. `98-openclash-utun`
* **部署路径**: `/etc/hotplug.d/net/98-openclash-utun`
* **触发时机**: Linux 内核创建 `utun` 虚拟网卡时（`ACTION=add DEVICENAME=utun`）
* **解决问题**: 
  - OpenClash TUN 模式下，因 `utun` 虚拟网卡掩码通常为 `/126`，导致内核路由表 `table main` 中缺少对整个 IPv6 Fake-IP 范围（如 `fdfe:dcba:9876::1/64`）的明细路由。
  - 本地进程发起 IPv6 连接分配到大于 `::3` 的 Fake-IP 时，会直接触发 `ENETUNREACH`（Network is unreachable），导致局域网或本机 IPv6 出海失败。
  - 本脚本在网卡出现时自动补齐 `ip -6 route replace "$fakeip_range6" dev utun`，彻底根治该问题。

### 2. `98-services-reload`
* **部署路径**: `/etc/hotplug.d/iface/98-services-reload`
* **触发时机**: WAN 接口重拨完成时（`ACTION=ifup INTERFACE=wan`）
* **解决问题**:
  - PPPoE 重新拨号后 WAN IP 发生变化，但某些对外主动建立 TLS/TCP 长连接的客户端（如探针客户端 `komari-agent` 等）可能会挂死在旧的已注销连接上（TCP 发送队列堆积 `Send-Q`），导致监控面板显示离线。
  - 本脚本在 WAN 接口就绪时自动重新拉起这类服务，实现自动断线自愈。

---

## 部署方法

在软路由执行以下命令安装：

```bash
# 1. 部署 utun 路由热插拔脚本
curl -fsSL https://raw.githubusercontent.com/violetaini/chitanda-openclash/main/contrib/hotplug/98-openclash-utun \
  -o /etc/hotplug.d/net/98-openclash-utun
chmod +x /etc/hotplug.d/net/98-openclash-utun

# 2. 部署 WAN 重拨自愈脚本（按需选择）
curl -fsSL https://raw.githubusercontent.com/violetaini/chitanda-openclash/main/contrib/hotplug/98-services-reload \
  -o /etc/hotplug.d/iface/98-services-reload
chmod +x /etc/hotplug.d/iface/98-services-reload
```

---

## 为什么不直接打包进 OpenClash？
1. **职责单一**：`chitanda-openclash` 仅专注 Mihomo 核心自定义分发与多 CDN 镜像加速，不侵入 OpenClash 自身网络生命周期代码。
2. **零维护负担**：完全解耦，避免上游代码更新重构造成 CI/CD Action 冲突或打包失败。
3. **宿主级健壮性**：无论未来如何更新、降级、重装 OpenClash 甚至更换为其他内核，宿主系统级别的 Hotplug 脚本都依然坚挺生效。
