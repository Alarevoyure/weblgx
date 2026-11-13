/** @weblgx-module **/

// Préférer weblgx_session_info ; retomber sur __session_info__ (alias / legacy).
const _session =
    globalThis.weblgx_session_info ||
    (globalThis.weblgx && globalThis.weblgx.__session_info__) ||
    (globalThis.weblgx && globalThis.weblgx.__session_info__) ||
    {};

export const session = _session;

if (globalThis.weblgx && "__session_info__" in globalThis.weblgx) {
    delete globalThis.weblgx.__session_info__;
}
if (globalThis.weblgx && globalThis.weblgx !== globalThis.weblgx && "__session_info__" in globalThis.weblgx) {
    delete globalThis.weblgx.__session_info__;
}
try {
    delete globalThis.weblgx_session_info;
} catch {
    // ignore (non-configurable)
}
