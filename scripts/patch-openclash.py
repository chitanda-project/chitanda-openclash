import os
import sys

def patch_openclash(repo_dir):
    print(f"[*] Applying Chitanda patches to OpenClash: {repo_dir}")
    lua_file = os.path.join(repo_dir, "luci-app-openclash", "root", "usr", "share", "openclash", "openclash_version.lua")
    sh_file = os.path.join(repo_dir, "luci-app-openclash", "root", "usr", "share", "openclash", "openclash_core.sh")

    # 1. Patch openclash_version.lua
    if os.path.exists(lua_file):
        with open(lua_file, "r", encoding="utf-8") as f:
            lua_content = f.read()

        # Remove legacy URL constant if present
        legacy_url = 'local CHITANDA_MIHOMO_VERSION_URL = "https://raw.githubusercontent.com/violetaini/chitanda/main/releases/mihomo/version.txt"\n'
        if legacy_url in lua_content:
            lua_content = lua_content.replace(legacy_url, "")

        chitanda_lua_funcs = r"""local function build_chitanda_version_urls(mod)
	local raw = "https://raw.githubusercontent.com/violetaini/chitanda/main/releases/mihomo/version.txt"
	local jsdelivr = "https://testingcf.jsdelivr.net/gh/violetaini/chitanda@main/releases/mihomo/version.txt"
	local jsdelivr_fastly = "https://fastly.jsdelivr.net/gh/violetaini/chitanda@main/releases/mihomo/version.txt"
	if mod == "0" or mod == "" or not mod then
		local urls = { raw, jsdelivr, jsdelivr_fastly }
		for _, cdn in ipairs(cdn_list()) do
			urls[#urls + 1] = cdn .. raw
		end
		return urls
	end
	if mod == "https://cdn.jsdelivr.net/" or mod == "https://fastly.jsdelivr.net/" or mod == "https://testingcf.jsdelivr.net/" then
		return { mod .. "gh/violetaini/chitanda@main/releases/mihomo/version.txt", raw, jsdelivr }
	end
	return { mod .. raw, raw, jsdelivr }
end

local function fetch_chitanda_mihomo_version(mod)
	local urls = build_chitanda_version_urls(mod)
	local raw = try_fetch(urls, function(buf)
		local version = trim((buf or ""):match("^[^\n\r]*") or "")
		return version:match("^v?%d+%.%d+%.%d+[%w%._%-]*$") ~= nil
	end)
	local version = trim((raw or ""):match("^[^\n\r]*") or "")
	if version:match("^v?%d+%.%d+%.%d+[%w%._%-]*$") then
		return version
	end
	return ""
end
"""

        oix_anchor = "function M.prepare_oix_cdn_data(force)"
        oix_start = lua_content.find(oix_anchor)
        if oix_start != -1:
            c_idx1 = lua_content.rfind("local function build_chitanda_version_urls", 0, oix_start)
            c_idx2 = lua_content.rfind("local function fetch_chitanda_mihomo_version", 0, oix_start)
            c_idx = c_idx1 if c_idx1 != -1 else c_idx2
            if c_idx != -1:
                lua_content = lua_content[:c_idx] + chitanda_lua_funcs + "\n" + lua_content[oix_start:]
            else:
                lua_content = lua_content[:oix_start] + chitanda_lua_funcs + "\n" + lua_content[oix_start:]

        # Update latest_only block to pass github_address_mod and cache core_meta
        if "core_meta_latest = fetch_chitanda_mihomo_version(github_address_mod)" not in lua_content:
            if "core_meta_latest = fetch_chitanda_mihomo_version()" in lua_content:
                lua_content = lua_content.replace(
                    "core_meta_latest = fetch_chitanda_mihomo_version()",
                    "core_meta_latest = fetch_chitanda_mihomo_version(github_address_mod)\n\t\t\tif core_meta_latest ~= \"\" then\n\t\t\t\tresult.core_meta = { { version = core_meta_latest, date = os.date(\"!%Y-%m-%dT%H:%M:%SZ\"), sha = \"chitanda\" } }\n\t\t\tend"
                )
            elif "if not cur_oix then\n\t\t\tlocal core_raw" in lua_content:
                lua_content = lua_content.replace(
                    "if not cur_oix then\n\t\t\tlocal core_raw",
                    "if not cur_oix then\n\t\t\tcore_meta_latest = fetch_chitanda_mihomo_version(github_address_mod)\n\t\t\tif core_meta_latest ~= \"\" then\n\t\t\t\tresult.core_meta = { { version = core_meta_latest, date = os.date(\"!%Y-%m-%dT%H:%M:%SZ\"), sha = \"chitanda\" } }\n\t\t\tend\n\n\t\t\tlocal core_raw"
                )
            elif "if not cur_oix then" in lua_content:
                lua_content = lua_content.replace(
                    "if not cur_oix then",
                    "if not cur_oix then\n\t\t\tcore_meta_latest = fetch_chitanda_mihomo_version(github_address_mod)\n\t\t\tif core_meta_latest ~= \"\" then\n\t\t\t\tresult.core_meta = { { version = core_meta_latest, date = os.date(\"!%Y-%m-%dT%H:%M:%SZ\"), sha = \"chitanda\" } }\n\t\t\tend"
                )

        # Update cache in latest_only block to preserve result.core_meta
        lua_content = lua_content.replace("blk.core_meta = nil", "blk.core_meta = result.core_meta")

        # Populate core_meta in full history fetch (right before result.latest = { ... plugin = (result.plugin[1])
        full_history_target = "\tresult.latest = {\n\t\tplugin = (result.plugin[1]"
        full_history_replacement = """\tif not cur_oix then
		local c_ver = fetch_chitanda_mihomo_version(github_address_mod)
		if c_ver and c_ver ~= "" then
			result.core_meta = { { version = c_ver, date = os.date("!%Y-%m-%dT%H:%M:%SZ"), sha = "chitanda" } }
		end
	end

	result.latest = {
		plugin = (result.plugin[1]"""
        if "local c_ver = fetch_chitanda_mihomo_version" not in lua_content and full_history_target in lua_content:
            lua_content = lua_content.replace(full_history_target, full_history_replacement, 1)

        with open(lua_file, "w", encoding="utf-8") as f:
            f.write(lua_content)
        print("  [+] Patched openclash_version.lua (with native proxy support & full cache populate)")

    # 2. Patch openclash_core.sh
    if os.path.exists(sh_file):
        with open(sh_file, "r", encoding="utf-8") as f:
            sh_content = f.read()

        # CHITANDA_CORE_RELEASE definition
        if "CHITANDA_CORE_RELEASE" not in sh_content:
            t1 = 'RELEASE_BRANCH=$(uci_get_config "release_branch" || echo "master")'
            i1 = t1 + '\nCHITANDA_CORE_RELEASE="https://github.com/violetaini/chitanda/releases/download"'
            sh_content = sh_content.replace(t1, i1, 1)

        # Version tracking file
        if "CHITANDA_CORE_VERSION_FILE" not in sh_content:
            t2 = 'TARGET_CORE_PATH="$meta_core_path"'
            i2 = t2 + '\nCHITANDA_CORE_VERSION_FILE="$meta_core_path/.chitanda-mihomo-version"\nCHITANDA_CORE_VERSION=$(cat "$CHITANDA_CORE_VERSION_FILE" 2>/dev/null)'
            sh_content = sh_content.replace(t2, i2, 1)

        # Update check condition
        old_cond = 'if [ -n "$DIRECT_CORE_URL" ] || [ "$CORE_CV" != "$CORE_LV" ] || [ -z "$CORE_CV" ]; then'
        new_cond = 'if [ -n "$DIRECT_CORE_URL" ] || [ "$CORE_TYPE" = "Meta" -a "$CHITANDA_CORE_VERSION" != "$CORE_LV" ] || [ "$CORE_CV" != "$CORE_LV" ] || [ -z "$CORE_CV" ]; then'
        if old_cond in sh_content:
            sh_content = sh_content.replace(old_cond, new_cond, 1)

        # Download URL with native github_address_mod support
        meta_download_block = """         if [ "$CORE_TYPE" = "Meta" ]; then
            CHITANDA_RAW_URL="${CHITANDA_CORE_RELEASE}/${CORE_LV}/clash-${CPU_MODEL}.tar.gz"
            if [ "$github_address_mod" != "0" ] && [ "$github_address_mod" != "https://cdn.jsdelivr.net/" ] && [ "$github_address_mod" != "https://fastly.jsdelivr.net/" ] && [ "$github_address_mod" != "https://testingcf.jsdelivr.net/" ]; then
               DOWNLOAD_URL="${github_address_mod}${CHITANDA_RAW_URL}"
            else
               DOWNLOAD_URL="${CHITANDA_RAW_URL}"
            fi
         elif [ "$github_address_mod" != "0" ]; then"""

        old_meta_block = """         if [ "$CORE_TYPE" = "Meta" ]; then
            DOWNLOAD_URL="${CHITANDA_CORE_RELEASE}/${CORE_LV}/clash-${CPU_MODEL}.tar.gz"
         elif [ "$github_address_mod" != "0" ]; then"""

        if old_meta_block in sh_content:
            sh_content = sh_content.replace(old_meta_block, meta_download_block, 1)
        elif "CHITANDA_RAW_URL" not in sh_content:
            t_orig = '         if [ "$github_address_mod" != "0" ]; then'
            if t_orig in sh_content:
                sh_content = sh_content.replace(t_orig, meta_download_block, 1)

        # Download retry fallback logic
        retry_fallback = """         if [ "$CORE_TYPE" = "Meta" ] && [ "$retry_count" -gt 1 ]; then
            if [ "$retry_count" -eq 2 ]; then
               DOWNLOAD_URL="https://ghfast.top/${CHITANDA_RAW_URL}"
            elif [ "$retry_count" -eq 3 ]; then
               DOWNLOAD_URL="https://gh-proxy.com/${CHITANDA_RAW_URL}"
            fi
         fi\n"""
        if "ghfast.top" not in sh_content:
            t_retry = 'while [ "$retry_count" -lt "$max_retries" ]; do\n         retry_count=$((retry_count + 1))\n'
            if t_retry in sh_content:
                sh_content = sh_content.replace(t_retry, t_retry + retry_fallback, 1)

        # Override direct url if pointing to vernesong for Meta
        old_direct = 'if [ -n "$2" ] && echo "$2" | grep -qE \'^https?://\'; then'
        new_direct = 'if [ -n "$2" ] && echo "$2" | grep -qE \'^https?://\' && ! ([ "$CORE_TYPE" = "Meta" ] && echo "$2" | grep -q "vernesong/OpenClash"); then'
        if old_direct in sh_content:
            sh_content = sh_content.replace(old_direct, new_direct, 1)

        # Version file recording on success
        if "CHITANDA_CORE_VERSION_FILE" in sh_content and "printf '%s\\n' \"$CORE_LV\" > \"$CHITANDA_CORE_VERSION_FILE\"" not in sh_content:
            t5 = 'LOG_TIP "【"$CORE_TYPE"】Core Update Successful"'
            i5 = 'if [ "$CORE_TYPE" = "Meta" ]; then\n                     printf \'%s\\n\' "$CORE_LV" > "$CHITANDA_CORE_VERSION_FILE"\n                  fi\n                  LOG_TIP "【"$CORE_TYPE"】Core Update Successful"'
            sh_content = sh_content.replace(t5, i5, 1)

        with open(sh_file, "w", encoding="utf-8") as f:
            f.write(sh_content)
        print("  [+] Patched openclash_core.sh (with native proxy support & CDN retry fallback)")

    # 3. Patch update.htm
    htm_file = os.path.join(repo_dir, "luci-app-openclash", "luasrc", "view", "openclash", "update.htm")
    if os.path.exists(htm_file):
        with open(htm_file, "r", encoding="utf-8") as f:
            htm_content = f.read()
        target_htm = "if (type === 'plugin') {"
        replacement_htm = """if (type === 'core' && !_isOix && smart_enable.value !== '1') {
            filename = 'clash-' + arch + '.tar.gz';
            var cv = (version && version !== '__latest__' && version.indexOf('alpha') === -1) ? version : 'v1.19.30';
            var rawChitanda = 'https://github.com/violetaini/chitanda/releases/download/' + cv + '/' + filename;
            if (addr && addr !== '' && classifyAddr(addr) !== 'raw' && !isJsDelivr) {
                return addr + rawChitanda;
            }
            return rawChitanda;
        }

        if (type === 'plugin') {"""
        if "rawChitanda" not in htm_content and target_htm in htm_content:
            htm_content = htm_content.replace(target_htm, replacement_htm, 1)
            with open(htm_file, "w", encoding="utf-8") as f:
                f.write(htm_content)
            print("  [+] Patched update.htm (Chitanda Meta core download URL)")

    # 4. Patch openclash.lua
    controller_file = os.path.join(repo_dir, "luci-app-openclash", "luasrc", "controller", "openclash.lua")
    if os.path.exists(controller_file):
        with open(controller_file, "r", encoding="utf-8") as f:
            c_content = f.read()
        target_c1 = 'local function build_version_url(cdn, file_type)\n\t\tif file_type == "core" and is_oix() then'
        replacement_c1 = '''local function build_version_url(cdn, file_type)
\t\tif file_type == "core" and not is_oix() then
\t\t\tlocal chitanda_raw = "https://raw.githubusercontent.com/violetaini/chitanda/main/releases/mihomo/version.txt"
\t\t\tlocal ctype = classify_cdn(cdn)
\t\t\tif ctype == "jsdelivr" then
\t\t\t\treturn cdn .. "gh/violetaini/chitanda@main/releases/mihomo/version.txt"
\t\t\telseif ctype == "proxy" then
\t\t\t\treturn cdn .. chitanda_raw
\t\t\tend
\t\t\treturn chitanda_raw
\t\tend

\t\tif file_type == "core" and is_oix() then'''

        target_c2 = 'local raw_ref = (core_ver ~= "" and core_ver ~= "__latest__") and core_ver or "core"\n\t\t\traw_core_url = "https://raw.githubusercontent.com/vernesong/OpenClash/" .. raw_ref .. "/" .. branch .. "/core_version"'
        replacement_c2 = '''if not is_oix() then
\t\t\traw_core_url = "https://raw.githubusercontent.com/violetaini/chitanda/main/releases/mihomo/version.txt"
\t\telse
\t\t\tlocal raw_ref = (core_ver ~= "" and core_ver ~= "__latest__") and core_ver or "core"
\t\t\traw_core_url = "https://raw.githubusercontent.com/vernesong/OpenClash/" .. raw_ref .. "/" .. branch .. "/core_version"
\t\tend'''

        if target_c1 in c_content:
            c_content = c_content.replace(target_c1, replacement_c1, 1)
        if target_c2 in c_content:
            c_content = c_content.replace(target_c2, replacement_c2, 1)
        with open(controller_file, "w", encoding="utf-8") as f:
            f.write(c_content)
        print("  [+] Patched openclash.lua (Chitanda CDN core version probe)")

    # 5. Patch openclash init.d (IPv6 fake-ip route on utun)
    init_file = os.path.join(repo_dir, "luci-app-openclash", "root", "etc", "init.d", "openclash")
    if os.path.exists(init_file):
        with open(init_file, "r", encoding="utf-8") as f:
            init_content = f.read()

        t_start = 'ip -6 rule add fwmark "$PROXY_FWMARK" table "$PROXY_ROUTE_TABLE" pref 1888\n         fi'
        r_start = ('ip -6 rule add fwmark "$PROXY_FWMARK" table "$PROXY_ROUTE_TABLE" pref 1888\n'
                   '            [ -z "$fakeip_range6" ] && fakeip_range6=$(uci_get_config "fakeip_range6" || echo "fdfe:dcba:9876::1/64")\n'
                   '            [ "$fakeip_range6" = "0" ] && fakeip_range6="fdfe:dcba:9876::1/64"\n'
                   '            ip -6 route replace "$fakeip_range6" dev utun 2>/dev/null\n'
                   '         fi')

        t_del = 'ip -6 route del default dev utun table "$PROXY_ROUTE_TABLE"\n\n   if [ -n "$FW4" ]; then'
        r_del = ('ip -6 route del default dev utun table "$PROXY_ROUTE_TABLE"\n'
                 '   [ -z "$fakeip_range6" ] && fakeip_range6=$(uci_get_config "fakeip_range6" || echo "fdfe:dcba:9876::1/64")\n'
                 '   [ "$fakeip_range6" = "0" ] && fakeip_range6="fdfe:dcba:9876::1/64"\n'
                 '   ip -6 route del "$fakeip_range6" dev utun 2>/dev/null\n\n'
                 '   if [ -n "$FW4" ]; then')

        # Check if upstream already implemented ANY route pointing fake-ip to utun
        has_upstream_fix = any(
            ("dev utun" in line and ("fakeip" in line.lower() or "9876" in line))
            for line in init_content.splitlines()
        )

        if not has_upstream_fix:
            if t_start in init_content:
                init_content = init_content.replace(t_start, r_start, 1)
            if t_del in init_content:
                init_content = init_content.replace(t_del, r_del, 1)
            with open(init_file, "w", encoding="utf-8") as f:
                f.write(init_content)
            print("  [+] Patched openclash init.d (IPv6 fake-ip utun route)")
        else:
            print("  [.] Upstream already includes IPv6 fake-ip utun route, skipping patch.")

    print("[*] OpenClash Chitanda patching complete!")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    patch_openclash(target)
