/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { uploadService } from "@web_editor/components/upload_progress_toast/upload_service";

/**
 * Pass the website being edited to upload RPCs. Loaded in web.assets_backend so
 * the patch is applied before the upload service is first started.
 */
patch(uploadService, {
    start(env, services) {
        let currentUploadWebsiteId = null;
        const getWebsiteId = (options) =>
            options?.websiteId || env.services.website?.currentWebsite?.id;
        const originalRpc = services.rpc;
        const rpc = (route, params, rpcOptions) => {
            const websiteId = currentUploadWebsiteId || getWebsiteId();
            if (
                (route === "/web_editor/attachment/add_data" ||
                    route === "/web_editor/attachment/add_url") &&
                websiteId
            ) {
                params = { ...params, website_id: websiteId };
            }
            return originalRpc(route, params, rpcOptions);
        };
        const result = super.start(env, { ...services, rpc });
        const originalUploadFiles = result.uploadFiles.bind(result);
        result.uploadFiles = async (files, options, onUploaded, setAbortCallback) => {
            currentUploadWebsiteId = getWebsiteId(options);
            try {
                return await originalUploadFiles(
                    files,
                    options,
                    onUploaded,
                    setAbortCallback
                );
            } finally {
                currentUploadWebsiteId = null;
            }
        };
        const originalUploadUrl = result.uploadUrl.bind(result);
        result.uploadUrl = async (url, options, onUploaded) => {
            currentUploadWebsiteId = getWebsiteId(options);
            try {
                return await originalUploadUrl(url, options, onUploaded);
            } finally {
                currentUploadWebsiteId = null;
            }
        };
        return result;
    },
});
