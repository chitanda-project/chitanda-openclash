<div align="center">

<img src="https://raw.githubusercontent.com/chitanda-project/chitanda/main/public/avatar.webp" alt="Chitanda" width="120" />

# 🌸 Chitanda OpenClash

**OpenWrt / ルーター向け次世代プロキシソリューション**

[![Release](https://img.shields.io/github/v/release/chitanda-project/chitanda-openclash?color=orange&style=flat-square)](https://github.com/chitanda-project/chitanda-openclash/releases)
[![CI](https://github.com/chitanda-project/chitanda-openclash/actions/workflows/chitanda-core-verify.yml/badge.svg)](https://github.com/chitanda-project/chitanda-openclash/actions)
[![Official Website](https://img.shields.io/badge/Official-chitanda.net-blue?style=flat-square)](https://chitanda.net)

<p align="center">
  <b>Chitanda OpenClash</b> は、OpenWrt / iStoreOS などのルーター環境向けに最適化された公式プロキシソリューションです。<br>
  次世代プロキシコア <b><a href="https://github.com/chitanda-project/chitanda">Chitanda Core (Mihomo)</a></b> を内蔵し、ネイティブ <b>Chitanda プロトコル</b> による家庭内・ゲートウェイ全透過プロキシを提供します。
</p>

</div>

> [!WARNING]
> ### ⚠️ 免責事項 (Disclaimer)
> 本プロジェクトおよび関連リソースは、学術研究、ネットワークセキュリティ検証、および正当な管理運用を目的として公開・提供されています。
> 
> 1. **法令遵守の義務**：本ソフトウェアおよび関連コードを利用する際は、**必ずご利用者ご自身の所在国・地域の法令および規則を遵守してください**。
> 2. **利用の禁止**：本ソフトウェアの利用が所在国または地域の法令・規則に違反する場合、**いかなる目的であっても本ソフトウェアのダウンロード、インストール、実行、および二次配布を行わないでください**。
> 3. **免責条項**：開発者およびプロジェクト保守管理者は、本ソフトウェアの使用、誤用、またはそれに関連して生じたいかなる損害、法的紛争、および責任についても一切の責任を負いません。

---


* [Wiki](https://github.com/vernesong/OpenClash/blob/dev/.github/skills/openclash-user-guide/SKILL.md)


下载地址
---


* IPK & APK [前往下载](https://github.com/vernesong/OpenClash/releases)


依赖
---

* luci
* luci-base
* dnsmasq-full
* bash
* curl
* ca-bundle
* ipset
* ip-full
* ruby
* ruby-yaml
* unzip
* iptables(iptables)
* kmod-ipt-nat(iptables)
* iptables-mod-tproxy(iptables)
* iptables-mod-extra(iptables)
* kmod-tun(TUN模式)
* luci-compat(Luci >= 19.07)
* ip6tables-mod-nat(iptables-ipv6)
* kmod-inet-diag(PROCESS-NAME)
* kmod-nft-tproxy(Firewall4)


编译
---


从 OpenWrt 的 [SDK](https://archive.openwrt.org/chaos_calmer/15.05.1/ar71xx/generic/OpenWrt-SDK-15.05.1-ar71xx-generic_gcc-4.8-linaro_uClibc-0.9.33.2.Linux-x86_64.tar.bz2) 编译
```bash
# 解压下载好的 SDK
curl -SLk --connect-timeout 30 --retry 2 "https://archive.openwrt.org/chaos_calmer/15.05.1/ar71xx/generic/OpenWrt-SDK-15.05.1-ar71xx-generic_gcc-4.8-linaro_uClibc-0.9.33.2.Linux-x86_64.tar.bz2" -o "/tmp/SDK.tar.bz2"
cd \tmp
tar xjf SDK.tar.bz2
cd OpenWrt-SDK-15.05.1-*

# Clone 项目
mkdir package/luci-app-openclash
cd package/luci-app-openclash
git init
git remote add -f origin https://github.com/vernesong/OpenClash.git
git config core.sparsecheckout true
echo "luci-app-openclash" >> .git/info/sparse-checkout
git pull --depth 1 origin master
git branch --set-upstream-to=origin/master master

# 编译 po2lmo (如果有po2lmo可跳过)
pushd luci-app-openclash/tools/po2lmo
make && sudo make install
popd

# 编译最新 CodeMirror 6 (插件内置，可跳过)
pushd luci-app-openclash/tools/codemirror
npm install
npx esbuild entry.js --bundle --format=iife --global-name=CM6 --minify --target=es2019 --outfile=../../root/www/luci-static/resources/openclash/js/cm6.min.js --legal-comments=none --loader:.css=text
rm -rf node_modules
popd

# 开始编译

# 先回退到SDK主目录
cd ../..
make package/luci-app-openclash/luci-app-openclash/compile V=99

# IPK文件位置
./bin/ar71xx/packages/base/luci-app-openclash_*-beta_all.ipk
```

```bash
# 同步源码
cd package/luci-app-openclash/luci-app-openclash
git pull

# 您也可以直接拷贝 `luci-app-openclash` 文件夹至其他 `OpenWrt` 项目的 `Package` 目录下随固件编译

make menuconfig
# 选择要编译的包 LuCI -> Applications -> luci-app-openclash

```


许可
---


* [MIT License](https://github.com/vernesong/OpenClash/blob/master/LICENSE)
* 内核 [Mihomo](https://github.com/MetaCubeX/mihomo) by [MetaCubeX](https://github.com/MetaCubeX)
* 本项目代码基于 [Luci For Clash](https://github.com/frainzy1477/luci-app-clash) by [frainzy1477](https://github.com/frainzy1477)
* IP检查 [IP](https://ip.skk.moe/) by [SukkaW](https://ip.skk.moe/)
* 控制面板 [zashboard](https://github.com/Zephyruso/zashboard) by [Zephyruso](https://github.com/Zephyruso)
* 控制面板 [yacd](https://github.com/haishanh/yacd) by [haishanh](https://github.com/haishanh)
* 流媒体解锁检测 [RegionRestrictionCheck](https://github.com/lmc999/RegionRestrictionCheck) by [lmc999](https://github.com/lmc999)

请作者喝杯咖啡
---

* PayPal
<p align="left">
    <a href='https://ko-fi.com/H2H41G5LS' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi6.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>
</p>

* USDT-BSC
<p align="left">
    <img width="300" src="https://github.com/vernesong/OpenClash/raw/master/img/USDT-Wallet.png">
</p>
