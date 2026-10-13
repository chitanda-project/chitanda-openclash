import os
import re
import sys

def patch_openclash(repo_dir):
    print(f"[*] Applying Chitanda patches to OpenClash: {repo_dir}")
    lua_file = os.path.join(repo_dir, "luci-app-openclash", "root", "usr", "share", "openclash", "openclash_version.lua")
    sh_file = os.path.join(repo_dir, "luci-app-openclash", "root", "usr", "share", "openclash", "openclash_core.sh")
    update_sh_file = os.path.join(repo_dir, "luci-app-openclash", "root", "usr", "share", "openclash", "openclash_update.sh")
    update_js_file = os.path.join(repo_dir, "luci-app-openclash", "root", "www", "luci-static", "resources", "openclash", "js", "update.js")
    htm_file = os.path.join(repo_dir, "luci-app-openclash", "luasrc", "view", "openclash", "update.htm")
    controller_file = os.path.join(repo_dir, "luci-app-openclash", "luasrc", "controller", "openclash.lua")
    makefile_file = os.path.join(repo_dir, "luci-app-openclash", "Makefile")
    uci_defaults_file = os.path.join(repo_dir, "luci-app-openclash", "root", "etc", "uci-defaults", "luci-openclash")
    init_file = os.path.join(repo_dir, "luci-app-openclash", "root", "etc", "init.d", "openclash")

    # 0. Generate version.txt from Makefile
    pkg_version = "0.48.002"
    if os.path.exists(makefile_file):
        with open(makefile_file, "r", encoding="utf-8") as f:
            m_content = f.read()
        m_match = re.search(r"PKG_VERSION:=([0-9\.]+)", m_content)
        if m_match:
            pkg_version = m_match.group(1).strip()
    
    version_txt_path = os.path.join(repo_dir, "version.txt")
    with open(version_txt_path, "w", encoding="utf-8") as f:
        f.write(f"v{pkg_version}\n")
    print(f"  [+] Wrote version.txt: v{pkg_version}")

    # 1. Patch openclash_version.lua
    if os.path.exists(lua_file):
        with open(lua_file, "r", encoding="utf-8") as f:
            lua_content = f.read()

        chitanda_lua_funcs = r"""local function build_chitanda_version_urls(mod)
	local raw = "https://raw.githubusercontent.com/chitanda-project/chitanda/main/releases/mihomo/version.txt"
	local jsdelivr = "https://testingcf.jsdelivr.net/gh/chitanda-project/chitanda@main/releases/mihomo/version.txt"
	local jsdelivr_fastly = "https://fastly.jsdelivr.net/gh/chitanda-project/chitanda@main/releases/mihomo/version.txt"
	if mod == "0" or mod == "" or not mod then
		local urls = { raw, jsdelivr, jsdelivr_fastly }
		for _, cdn in ipairs(cdn_list()) do
			urls[#urls + 1] = cdn .. raw
		end
		return urls
	end
	if mod == "https://cdn.jsdelivr.net/" or mod == "https://fastly.jsdelivr.net/" or mod == "https://testingcf.jsdelivr.net/" then
		return { mod .. "gh/chitanda-project/chitanda@main/releases/mihomo/version.txt", raw, jsdelivr }
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

local function build_chitanda_plugin_version_urls(mod)
	local raw = "https://raw.githubusercontent.com/chitanda-project/chitanda-openclash/main/version.txt"
	local jsdelivr = "https://testingcf.jsdelivr.net/gh/chitanda-project/chitanda-openclash@main/version.txt"
	local jsdelivr_fastly = "https://fastly.jsdelivr.net/gh/chitanda-project/chitanda-openclash@main/version.txt"
	if mod == "0" or mod == "" or not mod then
		local urls = { raw, jsdelivr, jsdelivr_fastly }
		for _, cdn in ipairs(cdn_list()) do
			urls[#urls + 1] = cdn .. raw
		end
		return urls
	end
	if mod == "https://cdn.jsdelivr.net/" or mod == "https://fastly.jsdelivr.net/" or mod == "https://testingcf.jsdelivr.net/" then
		return { mod .. "gh/chitanda-project/chitanda-openclash@main/version.txt", raw, jsdelivr }
	end
	return { mod .. raw, raw, jsdelivr }
end

local function fetch_chitanda_plugin_version(mod)
	local urls = build_chitanda_plugin_version_urls(mod)
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
            c_idx3 = lua_content.rfind("local function build_chitanda_plugin_version_urls", 0, oix_start)
            c_candidates = [x for x in [c_idx1, c_idx2, c_idx3] if x != -1]
            if len(c_candidates) > 0:
                c_min = min(c_candidates)
                lua_content = lua_content[:c_min] + chitanda_lua_funcs + "\n" + lua_content[oix_start:]
            else:
                lua_content = lua_content[:oix_start] + chitanda_lua_funcs + "\n" + lua_content[oix_start:]

        # Commit feed point to chitanda-openclash
        old_feed = 'local feed = "https://github.com/vernesong/OpenClash/commits/" .. path .. ".atom"'
        new_feed = 'local feed = "https://github.com/chitanda-project/chitanda-openclash/commits/main.atom"'
        if old_feed in lua_content:
            lua_content = lua_content.replace(old_feed, new_feed, 1)

        # Update latest_only plugin version fetch
        old_plugin_latest = """		local plugin_raw = try_fetch(build_fetch_urls(github_address_mod, "package/" .. branch .. "/version"))
		if plugin_raw and plugin_raw ~= "" then
			plugin_latest = trim(plugin_raw:match("^[^\n\r]*") or "")
		end"""
        new_plugin_latest = """		plugin_latest = fetch_chitanda_plugin_version(github_address_mod)
		if plugin_latest == "" then
			local plugin_raw = try_fetch(build_fetch_urls(github_address_mod, "package/" .. branch .. "/version"))
			if plugin_raw and plugin_raw ~= "" then
				plugin_latest = trim(plugin_raw:match("^[^\n\r]*") or "")
			end
		else
			result.plugin = { { version = plugin_latest, date = os.date("!%Y-%m-%dT%H:%M:%SZ"), message = "Chitanda OpenClash Release", sha = "chitanda" } }
		end"""
        if old_plugin_latest in lua_content:
            lua_content = lua_content.replace(old_plugin_latest, new_plugin_latest, 1)

        # Update latest_only core version fetch
        if "core_meta_latest = fetch_chitanda_mihomo_version(github_address_mod)" not in lua_content:
            if "if not cur_oix then\n\t\t\tlocal core_raw" in lua_content:
                lua_content = lua_content.replace(
                    "if not cur_oix then\n\t\t\tlocal core_raw",
                    "if not cur_oix then\n\t\t\tcore_meta_latest = fetch_chitanda_mihomo_version(github_address_mod)\n\t\t\tif core_meta_latest ~= \"\" then\n\t\t\t\tresult.core_meta = { { version = core_meta_latest, date = os.date(\"!%Y-%m-%dT%H:%M:%SZ\"), sha = \"chitanda\" } }\n\t\t\tend\n\n\t\t\tlocal core_raw",
                    1
                )
            elif "if not cur_oix then" in lua_content:
                lua_content = lua_content.replace(
                    "if not cur_oix then",
                    "if not cur_oix then\n\t\t\tcore_meta_latest = fetch_chitanda_mihomo_version(github_address_mod)\n\t\t\tif core_meta_latest ~= \"\" then\n\t\t\t\tresult.core_meta = { { version = core_meta_latest, date = os.date(\"!%Y-%m-%dT%H:%M:%SZ\"), sha = \"chitanda\" } }\n\t\t\tend",
                    1
                )

        # Cache retention in latest_only
        lua_content = lua_content.replace("blk.core_meta = nil", "blk.core_meta = result.core_meta")
        lua_content = lua_content.replace("blk.plugin = nil", "blk.plugin = result.plugin")

        # Full history fetch hook
        full_history_target = '\tresult.latest = {\n\t\tplugin = (result.plugin[1] and result.plugin[1].version) or "",'
        full_history_replacement = """\tif not cur_oix then
		local c_ver = fetch_chitanda_mihomo_version(github_address_mod)
		if c_ver and c_ver ~= "" then
			result.core_meta = { { version = c_ver, date = os.date("!%Y-%m-%dT%H:%M:%SZ"), sha = "chitanda" } }
		end
	end

	local p_ver = fetch_chitanda_plugin_version(github_address_mod)
	if p_ver and p_ver ~= "" and #result.plugin == 0 then
		result.plugin = { { version = p_ver, date = os.date("!%Y-%m-%dT%H:%M:%SZ"), message = "Chitanda OpenClash Release", sha = "chitanda" } }
	end

	result.latest = {
		plugin = (p_ver and p_ver ~= "") and p_ver or ((result.plugin[1] and result.plugin[1].version) or ""),"""
        if "local p_ver = fetch_chitanda_plugin_version" not in lua_content and full_history_target in lua_content:
            lua_content = lua_content.replace(full_history_target, full_history_replacement, 1)

        with open(lua_file, "w", encoding="utf-8") as f:
            f.write(lua_content)
        print("  [+] Patched openclash_version.lua (with Chitanda plugin and core version routing)")

    # 2. Patch openclash_core.sh
    if os.path.exists(sh_file):
        with open(sh_file, "r", encoding="utf-8") as f:
            sh_content = f.read()

        if "CHITANDA_CORE_RELEASE" not in sh_content:
            t1 = 'RELEASE_BRANCH=$(uci_get_config "release_branch" || echo "master")'
            i1 = t1 + '\nCHITANDA_CORE_RELEASE="https://github.com/chitanda-project/chitanda/releases/download"'
            sh_content = sh_content.replace(t1, i1, 1)

        if "CHITANDA_CORE_VERSION_FILE" not in sh_content:
            t2 = 'TARGET_CORE_PATH="$meta_core_path"'
            i2 = t2 + '\nCHITANDA_CORE_VERSION_FILE="$meta_core_path/.chitanda-mihomo-version"\nCHITANDA_CORE_VERSION=$(cat "$CHITANDA_CORE_VERSION_FILE" 2>/dev/null)'
            sh_content = sh_content.replace(t2, i2, 1)

        old_cond = 'if [ -n "$DIRECT_CORE_URL" ] || [ "$CORE_CV" != "$CORE_LV" ] || [ -z "$CORE_CV" ]; then'
        new_cond = 'if [ -n "$DIRECT_CORE_URL" ] || [ "$CORE_TYPE" = "Meta" -a "$CHITANDA_CORE_VERSION" != "$CORE_LV" ] || [ "$CORE_CV" != "$CORE_LV" ] || [ -z "$CORE_CV" ]; then'
        if old_cond in sh_content:
            sh_content = sh_content.replace(old_cond, new_cond, 1)

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

        old_direct = 'if [ -n "$2" ] && echo "$2" | grep -qE \'^https?://\'; then'
        new_direct = 'if [ -n "$2" ] && echo "$2" | grep -qE \'^https?://\' && ! ([ "$CORE_TYPE" = "Meta" ] && echo "$2" | grep -q "vernesong/OpenClash"); then'
        if old_direct in sh_content:
            sh_content = sh_content.replace(old_direct, new_direct, 1)

        if "CHITANDA_CORE_VERSION_FILE" in sh_content and "printf '%s\\n' \"$CORE_LV\" > \"$CHITANDA_CORE_VERSION_FILE\"" not in sh_content:
            t5 = 'LOG_TIP "【"$CORE_TYPE"】Core Update Successful"'
            i5 = 'if [ "$CORE_TYPE" = "Meta" ]; then\n                     printf \'%s\\n\' "$CORE_LV" > "$CHITANDA_CORE_VERSION_FILE"\n                  fi\n                  LOG_TIP "【"$CORE_TYPE"】Core Update Successful"'
            sh_content = sh_content.replace(t5, i5, 1)

        with open(sh_file, "w", encoding="utf-8") as f:
            f.write(sh_content)
        print("  [+] Patched openclash_core.sh (with Chitanda Core download routing)")

    # 3. Patch openclash_update.sh
    if os.path.exists(update_sh_file):
        with open(update_sh_file, "r", encoding="utf-8") as f:
            u_content = f.read()

        if "CHITANDA_PLUGIN_RELEASE" not in u_content:
            t_up_head = 'RELEASE_BRANCH=$(uci_get_config "release_branch" || echo "master")'
            i_up_head = t_up_head + '\nCHITANDA_PLUGIN_RELEASE="https://github.com/chitanda-project/chitanda-openclash/releases/download"'
            u_content = u_content.replace(t_up_head, i_up_head, 1)

        # Redirect direct download if pointing to vernesong
        direct_target = """if [ "$PLUGIN_DIRECT" -eq 1 ]; then
   # Direct download URL (historical version / downgrade) — skip version compare
   if [ "$PKG_TYPE" = "opkg" ]; then
      DOWNLOAD_URL="$3"
      DOWNLOAD_PATH="/tmp/openclash.ipk"
   else
      DOWNLOAD_URL="$3"
      DOWNLOAD_PATH="/tmp/openclash.apk"
   fi
   LAST_VER=$(echo "$DOWNLOAD_URL" | grep -oE 'luci-app-openclash[_-][0-9]+(\\.[0-9]+)*' | head -1 | sed 's/^luci-app-openclash[_-]//')"""
        direct_replacement = """if [ "$PLUGIN_DIRECT" -eq 1 ]; then
   # Direct download URL (historical version / downgrade) — redirect to Chitanda if vernesong requested
   LAST_VER=$(echo "$3" | grep -oE 'luci-app-openclash[_-][0-9]+(\\.[0-9]+)*' | head -1 | sed 's/^luci-app-openclash[_-]//')
   if echo "$3" | grep -q "vernesong/OpenClash"; then
      CHITANDA_PLUGIN_VER=$(echo "$LAST_VER" | sed 's/^v//')
      if [ "$PKG_TYPE" = "opkg" ]; then
         DOWNLOAD_URL="${CHITANDA_PLUGIN_RELEASE}/v${CHITANDA_PLUGIN_VER}/luci-app-openclash_${CHITANDA_PLUGIN_VER}_all.ipk"
         DOWNLOAD_PATH="/tmp/openclash.ipk"
      else
         DOWNLOAD_URL="${CHITANDA_PLUGIN_RELEASE}/v${CHITANDA_PLUGIN_VER}/luci-app-openclash-${CHITANDA_PLUGIN_VER}.apk"
         DOWNLOAD_PATH="/tmp/openclash.apk"
      fi
   else
      if [ "$PKG_TYPE" = "opkg" ]; then
         DOWNLOAD_URL="$3"
         DOWNLOAD_PATH="/tmp/openclash.ipk"
      else
         DOWNLOAD_URL="$3"
         DOWNLOAD_PATH="/tmp/openclash.apk"
      fi
   fi"""
        if direct_target in u_content:
            u_content = u_content.replace(direct_target, direct_replacement, 1)

        # Replace standard plugin download URLs
        old_download_block = """   if [ "$github_address_mod" != "0" ]; then
      if [ "$github_address_mod" == "https://cdn.jsdelivr.net/" ] || [ "$github_address_mod" == "https://fastly.jsdelivr.net/" ] || [ "$github_address_mod" == "https://testingcf.jsdelivr.net/" ]; then
         if [ "$PKG_TYPE" = "opkg" ]; then
            DOWNLOAD_URL="${github_address_mod}gh/vernesong/OpenClash@package/${RELEASE_BRANCH}/luci-app-openclash_${LAST_VER}_all.ipk"
            DOWNLOAD_PATH="/tmp/openclash.ipk"
         else
            DOWNLOAD_URL="${github_address_mod}gh/vernesong/OpenClash@package/${RELEASE_BRANCH}/luci-app-openclash-${LAST_VER}.apk"
            DOWNLOAD_PATH="/tmp/openclash.apk"
         fi
      else
         if [ "$PKG_TYPE" = "opkg" ]; then
            DOWNLOAD_URL="${github_address_mod}https://raw.githubusercontent.com/vernesong/OpenClash/package/${RELEASE_BRANCH}/luci-app-openclash_${LAST_VER}_all.ipk"
            DOWNLOAD_PATH="/tmp/openclash.ipk"
         else
            DOWNLOAD_URL="${github_address_mod}https://raw.githubusercontent.com/vernesong/OpenClash/package/${RELEASE_BRANCH}/luci-app-openclash-${LAST_VER}.apk"
            DOWNLOAD_PATH="/tmp/openclash.apk"
         fi
      fi
   else
      if [ "$PKG_TYPE" = "opkg" ]; then
         DOWNLOAD_URL="https://raw.githubusercontent.com/vernesong/OpenClash/package/${RELEASE_BRANCH}/luci-app-openclash_${LAST_VER}_all.ipk"
         DOWNLOAD_PATH="/tmp/openclash.ipk"
      else
         DOWNLOAD_URL="https://raw.githubusercontent.com/vernesong/OpenClash/package/${RELEASE_BRANCH}/luci-app-openclash-${LAST_VER}.apk"
         DOWNLOAD_PATH="/tmp/openclash.apk"
      fi
   fi"""

        new_download_block = """   CHITANDA_PLUGIN_VER=$(echo "$LAST_VER" | sed 's/^v//')
   if [ "$PKG_TYPE" = "opkg" ]; then
      CHITANDA_PLUGIN_PKG="luci-app-openclash_${CHITANDA_PLUGIN_VER}_all.ipk"
      DOWNLOAD_PATH="/tmp/openclash.ipk"
   else
      CHITANDA_PLUGIN_PKG="luci-app-openclash-${CHITANDA_PLUGIN_VER}.apk"
      DOWNLOAD_PATH="/tmp/openclash.apk"
   fi
   CHITANDA_PLUGIN_RAW_URL="${CHITANDA_PLUGIN_RELEASE}/v${CHITANDA_PLUGIN_VER}/${CHITANDA_PLUGIN_PKG}"
   if [ "$github_address_mod" != "0" ] && [ "$github_address_mod" != "https://cdn.jsdelivr.net/" ] && [ "$github_address_mod" != "https://fastly.jsdelivr.net/" ] && [ "$github_address_mod" != "https://testingcf.jsdelivr.net/" ]; then
      DOWNLOAD_URL="${github_address_mod}${CHITANDA_PLUGIN_RAW_URL}"
   else
      DOWNLOAD_URL="${CHITANDA_PLUGIN_RAW_URL}"
   fi"""

        if old_download_block in u_content:
            u_content = u_content.replace(old_download_block, new_download_block, 1)

        # Retry fallback for plugin download
        plugin_retry_fallback = """      if [ "$retry_count" -gt 1 ] && [ -n "$CHITANDA_PLUGIN_RAW_URL" ]; then
         if [ "$retry_count" -eq 2 ]; then
            DOWNLOAD_URL="https://ghfast.top/${CHITANDA_PLUGIN_RAW_URL}"
         elif [ "$retry_count" -eq 3 ]; then
            DOWNLOAD_URL="https://gh-proxy.com/${CHITANDA_PLUGIN_RAW_URL}"
         fi
      fi\n"""
        if "ghfast.top" not in u_content and "CHITANDA_PLUGIN_RAW_URL" in u_content:
            t_u_retry = 'while [ "$retry_count" -lt "$max_retries" ]; do\n      retry_count=$((retry_count + 1))\n'
            if t_u_retry in u_content:
                u_content = u_content.replace(t_u_retry, t_u_retry + plugin_retry_fallback, 1)

        with open(update_sh_file, "w", encoding="utf-8") as f:
            f.write(u_content)
        print("  [+] Patched openclash_update.sh (with Chitanda OpenClash package download routing)")

    # 4. Patch update.js
    if os.path.exists(update_js_file):
        with open(update_js_file, "r", encoding="utf-8") as f:
            js_content = f.read()

        target_js = """        if (type === 'plugin') {
            var verNoV = version.replace(/^v/, '');
            if (pkgType === 'apk') {
                filename = 'luci-app-openclash-' + verNoV + '.apk';
            } else {
                filename = 'luci-app-openclash_' + verNoV + '_all.ipk';
            }
            pathPrefix = 'package/' + branch;
        } else {
            filename = 'clash-' + arch + '.tar.gz';
            var coreSubPath = (smart_enable.value === '1') ? 'smart' : 'meta';
            pathPrefix = 'core/' + branch + '/' + coreSubPath;
        }"""

        replacement_js = """        if (type === 'plugin') {
            var verNoV = version ? version.replace(/^v/, '') : '';
            if (pkgType === 'apk') {
                filename = 'luci-app-openclash-' + verNoV + '.apk';
            } else {
                filename = 'luci-app-openclash_' + verNoV + '_all.ipk';
            }
            var rawChitandaPlugin = 'https://github.com/chitanda-project/chitanda-openclash/releases/download/v' + verNoV + '/' + filename;
            if (addr && addr !== '' && classifyAddr(addr) !== 'raw' && !isJsDelivr) {
                return addr + rawChitandaPlugin;
            }
            return rawChitandaPlugin;
        } else if (type === 'core' && !isOix && smart_enable.value !== '1') {
            filename = 'clash-' + arch + '.tar.gz';
            var cv = (version && version !== '__latest__' && version.indexOf('alpha') === -1) ? version : 'v1.19.32';
            var rawChitandaCore = 'https://github.com/chitanda-project/chitanda/releases/download/' + cv + '/' + filename;
            if (addr && addr !== '' && classifyAddr(addr) !== 'raw' && !isJsDelivr) {
                return addr + rawChitandaCore;
            }
            return rawChitandaCore;
        } else {
            filename = 'clash-' + arch + '.tar.gz';
            var coreSubPath = (smart_enable.value === '1') ? 'smart' : 'meta';
            pathPrefix = 'core/' + branch + '/' + coreSubPath;
        }"""
        if target_js in js_content:
            js_content = js_content.replace(target_js, replacement_js, 1)
            with open(update_js_file, "w", encoding="utf-8") as f:
                f.write(js_content)
            print("  [+] Patched update.js (Chitanda Plugin and Core Web UI download URLs)")

    # 5. Patch update.htm (fallback for older templates)
    if os.path.exists(htm_file):
        with open(htm_file, "r", encoding="utf-8") as f:
            htm_content = f.read()
        target_htm = "if (type === 'plugin') {"
        replacement_htm = """if (type === 'core' && !_isOix && smart_enable.value !== '1') {
            filename = 'clash-' + arch + '.tar.gz';
            var cv = (version && version !== '__latest__' && version.indexOf('alpha') === -1) ? version : 'v1.19.32';
            var rawChitanda = 'https://github.com/chitanda-project/chitanda/releases/download/' + cv + '/' + filename;
            if (addr && addr !== '' && classifyAddr(addr) !== 'raw' && !isJsDelivr) {
                return addr + rawChitanda;
            }
            return rawChitanda;
        }

        if (type === 'plugin') {
            var verNoV = version ? version.replace(/^v/, '') : '';
            var pkgFilename = (_pkgType === 'apk') ? ('luci-app-openclash-' + verNoV + '.apk') : ('luci-app-openclash_' + verNoV + '_all.ipk');
            var rawChitandaPlugin = 'https://github.com/chitanda-project/chitanda-openclash/releases/download/v' + verNoV + '/' + pkgFilename;
            if (addr && addr !== '' && classifyAddr(addr) !== 'raw' && !isJsDelivr) {
                return addr + rawChitandaPlugin;
            }
            return rawChitandaPlugin;
        }

        if (false && type === 'plugin') {"""
        if "rawChitanda" not in htm_content and target_htm in htm_content:
            htm_content = htm_content.replace(target_htm, replacement_htm, 1)
            with open(htm_file, "w", encoding="utf-8") as f:
                f.write(htm_content)
            print("  [+] Patched update.htm (Chitanda Plugin and Core fallback URLs)")

    # 6. Patch openclash.lua
    if os.path.exists(controller_file):
        with open(controller_file, "r", encoding="utf-8") as f:
            c_content = f.read()

        target_c1 = 'local function build_version_url(cdn, file_type)\n\t\tif file_type == "core" and not is_oix() then'
        replacement_c1 = '''local function build_version_url(cdn, file_type)
\t\tif file_type == "plugin" then
\t\t\tlocal chitanda_plugin_raw = "https://raw.githubusercontent.com/chitanda-project/chitanda-openclash/main/version.txt"
\t\t\tlocal ctype = classify_cdn(cdn)
\t\t\tif ctype == "jsdelivr" then
\t\t\t\treturn cdn .. "gh/chitanda-project/chitanda-openclash@main/version.txt"
\t\t\telseif ctype == "proxy" then
\t\t\t\treturn cdn .. chitanda_plugin_raw
\t\t\tend
\t\t\treturn chitanda_plugin_raw
\t\tend

\t\tif file_type == "core" and not is_oix() then'''

        target_ann = 'https://raw.githubusercontent.com/vernesong/OpenClash/dev/announcement'
        replacement_ann = 'https://raw.githubusercontent.com/chitanda-project/chitanda-openclash/main/announcement'

        if target_c1 in c_content:
            c_content = c_content.replace(target_c1, replacement_c1, 1)
        if target_ann in c_content:
            c_content = c_content.replace(target_ann, replacement_ann, 1)

        # Update org references
        c_content = c_content.replace("violetaini/chitanda", "chitanda-project/chitanda")

        with open(controller_file, "w", encoding="utf-8") as f:
            f.write(c_content)
        print("  [+] Patched openclash.lua (Chitanda CDN plugin & core probe)")

    # 7. Patch uci-defaults/luci-openclash
    if os.path.exists(uci_defaults_file):
        with open(uci_defaults_file, "r", encoding="utf-8") as f:
            uci_content = f.read()

        uci_http_fix = """#increase LuCI POST content size limit for large OpenClash configs / subscriptions
if [ -f "/usr/share/ucode/luci/http.uc" ]; then
\tsed -i 's/HTTP_MAX_CONTENT = 1024\\*100;/HTTP_MAX_CONTENT = 1024\\*1024\\*10;/g' /usr/share/ucode/luci/http.uc 2>/dev/null
fi
if [ -f "/usr/lib/lua/luci/http.lua" ]; then
\tsed -i 's/HTTP_MAX_CONTENT[ \\t]*=[ \\t]*1024\\*100/HTTP_MAX_CONTENT      = 1024\\*1024\\*10/g' /usr/lib/lua/luci/http.lua 2>/dev/null
fi
"""
        if "HTTP_MAX_CONTENT" not in uci_content:
            target_uhttpd = 'if [ -x /etc/init.d/uhttpd ]; then\n\tuci -q set uhttpd.@uhttpd[0].max_requests=50\n\tuci -q set uhttpd.@uhttpd[0].script_timeout=3600\n\tuci -q commit uhttpd\nfi'
            if target_uhttpd in uci_content:
                uci_content = uci_content.replace(target_uhttpd, target_uhttpd + "\n\n" + uci_http_fix, 1)
                with open(uci_defaults_file, "w", encoding="utf-8") as f:
                    f.write(uci_content)
                print("  [+] Patched uci-defaults/luci-openclash (LuCI HTTP_MAX_CONTENT limit increase)")

    # 8. Patch init.d/openclash
    if os.path.exists(init_file):
        with open(init_file, "r", encoding="utf-8") as f:
            init_content = f.read()

        init_http_fix = """boot()
{
   [ -f /usr/share/ucode/luci/http.uc ] && sed -i 's/HTTP_MAX_CONTENT = 1024\\*100;/HTTP_MAX_CONTENT = 1024\\*1024\\*10;/g' /usr/share/ucode/luci/http.uc 2>/dev/null
   [ -f /usr/lib/lua/luci/http.lua ] && sed -i 's/HTTP_MAX_CONTENT[ \\t]*=[ \\t]*1024\\*100/HTTP_MAX_CONTENT      = 1024\\*1024\\*10/g' /usr/lib/lua/luci/http.lua 2>/dev/null"""
        if "HTTP_MAX_CONTENT" not in init_content and "boot()\n{\n   delay_start=" in init_content:
            init_content = init_content.replace("boot()\n{\n   delay_start=", init_http_fix + "\n   delay_start=", 1)
            with open(init_file, "w", encoding="utf-8") as f:
                f.write(init_content)
            print("  [+] Patched init.d/openclash (LuCI HTTP_MAX_CONTENT boot check)")

    print("[*] OpenClash Chitanda patching complete!")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    patch_openclash(target)
