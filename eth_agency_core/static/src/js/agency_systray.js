/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class AgencyNotificationSystray extends Component {
    static template = "eth_agency_core.AgencyNotificationSystray";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            pendingRequests: 0,
            unreadMessages: 0,
            pendingRegistrations: 0,
        });

        onWillStart(async () => {
            await this.loadCounts();
        });

        // Refresh every 30 seconds
        this.interval = setInterval(() => {
            this.loadCounts();
        }, 30000);
    }

    async loadCounts() {
        // Get pending update requests count
        try {
            const pendingRequests = await this.orm.searchCount("agency.update.request", [
                ["state", "=", "pending"]
            ]);
            this.state.pendingRequests = pendingRequests;
        } catch (e) {
            this.state.pendingRequests = 0;
        }

        // Get unread messages count
        try {
            const conversations = await this.orm.searchRead(
                "agency.conversation",
                [["state", "=", "open"]],
                ["unread_admin_count"]
            );
            this.state.unreadMessages = conversations.reduce((sum, conv) => sum + (conv.unread_admin_count || 0), 0);
        } catch (e) {
            this.state.unreadMessages = 0;
        }

        // Get pending registrations count
        try {
            const pendingRegistrations = await this.orm.searchCount("agency.registration", [
                ["state", "=", "pending"]
            ]);
            this.state.pendingRegistrations = pendingRegistrations;
        } catch (e) {
            this.state.pendingRegistrations = 0;
        }
    }

    async openUpdateRequests() {
        try {
            await this.action.doAction("eth_agency_core.action_agency_update_request");
        } catch (e) {
            // Fallback if action not found
            await this.action.doAction({
                type: "ir.actions.act_window",
                name: "Update Requests",
                res_model: "agency.update.request",
                view_mode: "list,form",
                target: "current",
            });
        }
    }

    async openMessages() {
        try {
            await this.action.doAction("eth_agency_core.action_agency_conversation");
        } catch (e) {
            await this.action.doAction({
                type: "ir.actions.act_window",
                name: "Agency Messages",
                res_model: "agency.conversation",
                view_mode: "list,form",
                target: "current",
            });
        }
    }

    async openRegistrations() {
        try {
            await this.action.doAction("eth_agency_core.action_agency_registration");
        } catch (e) {
            await this.action.doAction({
                type: "ir.actions.act_window",
                name: "Registrations",
                res_model: "agency.registration",
                view_mode: "list,form",
                target: "current",
            });
        }
    }

    willUnmount() {
        if (this.interval) {
            clearInterval(this.interval);
        }
    }
}

AgencyNotificationSystray.template = "eth_agency_core.AgencyNotificationSystray";

export const systrayItem = {
    Component: AgencyNotificationSystray,
};

registry.category("systray").add("eth_agency_core.AgencyNotificationSystray", systrayItem, { sequence: 25 });
