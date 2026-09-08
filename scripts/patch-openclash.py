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

        # Version file recording on success
        if "CHITANDA_CORE_VERSION_FILE" in sh_content and "printf '%s\\n' \"$CORE_LV\" > \"$CHITANDA_CORE_VERSION_FILE\"" not in sh_content:
            t5 = 'LOG_TIP "【"$CORE_TYPE"】Core Update Successful"'
            i5 = 'if [ "$CORE_TYPE" = "Meta" ]; then\n                     printf \'%s\\n\' "$CORE_LV" > "$CHITANDA_CORE_VERSION_FILE"\n                  fi\n                  LOG_TIP "【"$CORE_TYPE"】Core Update Successful"'
            sh_content = sh_content.replace(t5, i5, 1)

        with open(sh_file, "w", encoding="utf-8") as f:
            f.write(sh_content)
        print("  [+] Patched openclash_core.sh (with native proxy support & CDN retry fallback)")

    print("[*] OpenClash Chitanda patching complete!")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    patch_openclash(target)
