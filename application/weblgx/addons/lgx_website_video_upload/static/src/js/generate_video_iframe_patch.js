/** @odoo-module **/

/**
 * Prevent website's generateVideoIframe() from wiping uploaded native <video>
 * blocks: that helper empties every .media_iframe_video without an iframe.
 * We use .media_video_upload instead, but also guard if both classes exist.
 */
document.addEventListener(
    "DOMContentLoaded",
    () => {
        for (const el of document.querySelectorAll(".media_video_upload")) {
            // Ensure native video src is present after save/load.
            const videoEl = el.querySelector(":scope > video");
            const src = el.dataset.oeExpression || el.dataset.src;
            if (videoEl && src && !videoEl.getAttribute("src")) {
                videoEl.setAttribute("src", src);
            }
        }
    },
    { once: true }
);
