import { App, Plugin, TAbstractFile, TFile } from "obsidian";

import { GatewayClient } from "../api/gatewayClient";
import type { PluginSettings } from "../settings";
import type { GatewayFileEventPayload, VaultEventType } from "../types";
import { sha256Hex } from "../utils/hash";
import { isMarkdownPath, shouldSkipPath } from "../utils/fileFilters";

interface PendingEvent {
	eventType: VaultEventType;
	path: string;
	oldPath?: string;
}

export class VaultSyncService {
	private readonly pendingEvents = new Map<string, PendingEvent>();
	private readonly timers = new Map<string, number>();

	constructor(
		private readonly app: App,
		private readonly gatewayClient: GatewayClient,
		private readonly getSettings: () => PluginSettings,
		private readonly ensureAuthenticated: () => Promise<string>,
	) {}

	attach(plugin: Plugin): void {
		plugin.registerEvent(this.app.vault.on("modify", (file) => this.onModify(file)));
		plugin.registerEvent(this.app.vault.on("create", (file) => this.onCreate(file)));
		plugin.registerEvent(this.app.vault.on("delete", (file) => this.onDelete(file)));
		plugin.registerEvent(this.app.vault.on("rename", (file, oldPath) => this.onRename(file, oldPath)));

		plugin.register(() => {
			for (const timer of this.timers.values()) {
				window.clearTimeout(timer);
			}
			this.timers.clear();
			this.pendingEvents.clear();
		});
	}

	private onModify(file: TAbstractFile): void {
		this.enqueue({
			eventType: "modify",
			path: file.path,
		});
	}

	private onCreate(file: TAbstractFile): void {
		this.enqueue({
			eventType: "create",
			path: file.path,
		});
	}

	private onDelete(file: TAbstractFile): void {
		this.enqueue({
			eventType: "delete",
			path: file.path,
		});
	}

	private onRename(file: TAbstractFile, oldPath: string): void {
		this.enqueue({
			eventType: "rename",
			path: file.path,
			oldPath,
		});
	}

	private enqueue(event: PendingEvent): void {
		const settings = this.getSettings();
		if (!settings.syncEnabled) {
			return;
		}
		if (this.shouldSkipEvent(event)) {
			return;
		}

		const key = this.getDebounceKey(event);
		const existingTimer = this.timers.get(key);
		if (existingTimer !== undefined) {
			window.clearTimeout(existingTimer);
		}

		this.pendingEvents.set(key, event);
		const timer = window.setTimeout(() => {
			void this.flush(key);
		}, settings.debounceMs);
		this.timers.set(key, timer);
	}

	private shouldSkipEvent(event: PendingEvent): boolean {
		const configDir = this.app.vault.configDir;
		if (event.eventType === "rename" && event.oldPath) {
			const oldSkipped = shouldSkipPath(event.oldPath, configDir);
			const newSkipped = shouldSkipPath(event.path, configDir);
			if (oldSkipped && newSkipped) {
				return true;
			}
		}

		if (shouldSkipPath(event.path, configDir)) {
			return true;
		}

		if (event.eventType === "rename") {
			const oldIsMd = event.oldPath ? isMarkdownPath(event.oldPath) : false;
			return !isMarkdownPath(event.path) && !oldIsMd;
		}
		return !isMarkdownPath(event.path);
	}

	private getDebounceKey(event: PendingEvent): string {
		if (event.eventType === "rename" && event.oldPath) {
			return `${event.eventType}:${event.oldPath}->${event.path}`;
		}
		return `${event.eventType}:${event.path}`;
	}

	private async flush(key: string): Promise<void> {
		const event = this.pendingEvents.get(key);
		this.pendingEvents.delete(key);
		this.timers.delete(key);
		if (!event) {
			return;
		}

		const token = await this.ensureAuthenticated();
		const payload = await this.buildPayload(event);
		await this.gatewayClient.sendFileEvent(token, payload);
	}

	private async buildPayload(event: PendingEvent): Promise<GatewayFileEventPayload> {
		const timestamp = new Date().toISOString();
		if (event.eventType === "create" || event.eventType === "modify") {
			const file = this.app.vault.getAbstractFileByPath(event.path);
			if (!(file instanceof TFile)) {
				throw new Error(`Expected TFile for ${event.eventType}: ${event.path}`);
			}
			const content = await this.app.vault.cachedRead(file);
			const sha256 = await sha256Hex(content);
			return {
				event_type: event.eventType,
				path: event.path,
				content,
				sha256,
				timestamp,
			};
		}

		if (event.eventType === "rename") {
			return {
				event_type: "rename",
				path: event.path,
				old_path: event.oldPath,
				timestamp,
			};
		}

		return {
			event_type: "delete",
			path: event.path,
			timestamp,
		};
	}
}

