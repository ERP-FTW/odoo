/** @odoo-module */

export function extractCardPointeToken(eventData) {
    if (!eventData || typeof eventData !== "object") return "";
    return eventData.token || eventData.account || "";
}
