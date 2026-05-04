import { App, Notice, Plugin, TAbstractFile, TFile } from "obsidian";

import { GatewayClient } from "../api/gatewayClient";
import type { PluginSettings } from "../settings";
import type { GatewayFileEventPayload, VaultEventType } from "../types";
import { sha256Hex, sha256HexFromArrayBuffer } from "../utils/hash";
import { isMarkdownPath, isMediaPath, shouldSkipPath } from "../utils/fileFilters";

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
		console.debug(`[VAULT_SYNC] onCreate event: ${file.path} (isMedia: ${isMediaPath(file.path)}, isMarkdown: ${isMarkdownPath(file.path)})`);
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
				console.debug(`[VAULT_SYNC] Skipping rename event (both paths skipped): ${event.oldPath} -> ${event.path}`);
				return true;
			}
		}

		if (shouldSkipPath(event.path, configDir)) {
			console.debug(`[VAULT_SYNC] Skipping event (path filtered): ${event.path}`);
			return true;
		}

		if (event.eventType === "rename") {
			const oldIsMd = event.oldPath ? isMarkdownPath(event.oldPath) : false;
			const oldIsMedia = event.oldPath ? isMediaPath(event.oldPath) : false;
			const newIsMd = isMarkdownPath(event.path);
			const newIsMedia = isMediaPath(event.path);
			const shouldSkip = !newIsMd && !newIsMedia && !oldIsMd && !oldIsMedia;
			if (shouldSkip) {
				console.debug(`[VAULT_SYNC] Skipping rename event (not md/media): ${event.oldPath} -> ${event.path}`);
			}
			return shouldSkip;
		}
		const isMd = isMarkdownPath(event.path);
		const isMedia = isMediaPath(event.path);
		const shouldSkip = !isMd && !isMedia;
		if (shouldSkip) {
			console.debug(`[VAULT_SYNC] Skipping event (not md/media): ${event.path}`);
		}
		return shouldSkip;
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

		console.debug(`[VAULT_SYNC] Flushing event: ${event.eventType} for ${event.path}`);
		try {
			const token = await this.ensureAuthenticated();
			const payload = await this.buildPayload(event);
			console.debug(`[VAULT_SYNC] Sending payload: ${event.eventType} for ${event.path} (is_media: ${payload.is_media ?? false})`);
			await this.gatewayClient.sendFileEvent(token, payload);
			console.debug(`[VAULT_SYNC] Successfully sent: ${event.eventType} for ${event.path}`);
		} catch (error: unknown) {
			const message = error instanceof Error ? error.message : "Unknown error";
			console.error(`[VAULT_SYNC] Error syncing ${event.path}:`, error);
			new Notice(`❌ Ошибка синхронизации ${event.path}: ${message}`);
		}
	}

	async syncAllFiles(token: string): Promise<{ success: number; errors: number }> {
		const configDir = this.app.vault.configDir;
		const allFiles = this.app.vault.getAllLoadedFiles().filter((f): f is TFile => f instanceof TFile);
		let success = 0;
		let errors = 0;

		for (const file of allFiles) {
			if (shouldSkipPath(file.path, configDir)) {
				continue;
			}

			try {
				const timestamp = new Date().toISOString();
				let payload: GatewayFileEventPayload;

				if (isMediaPath(file.path)) {
					const arrayBuffer = await this.app.vault.readBinary(file);
					const sha256 = await sha256HexFromArrayBuffer(arrayBuffer);
					const base64 = this.arrayBufferToBase64(arrayBuffer);
					const contentType = this.getMediaContentType(file.path);

					payload = {
						event_type: "create",
						path: file.path,
						sha256,
						timestamp,
						is_media: true,
						media_content_base64: base64,
						media_content_type: contentType,
					};
				} else if (isMarkdownPath(file.path)) {
					const content = await this.app.vault.cachedRead(file);
					const sha256 = await sha256Hex(content);

					payload = {
						event_type: "create",
						path: file.path,
						content,
						sha256,
						timestamp,
					};
				} else {
					continue;
				}

				await this.gatewayClient.sendFileEvent(token, payload);
				success++;
			} catch (error: unknown) {
				errors++;
				const message = error instanceof Error ? error.message : "Unknown error";
				new Notice(`❌ Ошибка загрузки ${file.path}: ${message}`);
			}
		}

		return { success, errors };
	}

	private arrayBufferToBase64(buffer: ArrayBuffer): string {
		const bytes = new Uint8Array(buffer);
		let binary = "";
		const chunkSize = 8192;
		for (let i = 0; i < bytes.length; i += chunkSize) {
			const chunk = bytes.subarray(i, i + chunkSize);
			binary += String.fromCharCode(...chunk);
		}
		return btoa(binary);
	}

	private getMediaContentType(path: string): string {
		const ext = path.split(".").pop()?.toLowerCase() ?? "";
		const contentTypes: Record<string, string> = {
			pdf: "application/pdf",
			png: "image/png",
			jpg: "image/jpeg",
			jpeg: "image/jpeg",
			gif: "image/gif",
			webp: "image/webp",
			bmp: "image/bmp",
			ico: "image/x-icon",
			svg: "image/svg+xml",
		};
		return contentTypes[ext] ?? "application/octet-stream";
	}

	private async buildPayload(event: PendingEvent): Promise<GatewayFileEventPayload> {
		const timestamp = new Date().toISOString();
		if (event.eventType === "create" || event.eventType === "modify") {
			const file = this.app.vault.getAbstractFileByPath(event.path);
			if (!(file instanceof TFile)) {
				throw new Error(`Expected TFile for ${event.eventType}: ${event.path}`);
			}

			if (isMediaPath(event.path)) {
				const arrayBuffer = await this.app.vault.readBinary(file);
				const sha256 = await sha256HexFromArrayBuffer(arrayBuffer);
				const base64 = this.arrayBufferToBase64(arrayBuffer);
				const contentType = this.getMediaContentType(event.path);

				return {
					event_type: event.eventType,
					path: event.path,
					sha256,
					timestamp,
					is_media: true,
					media_content_base64: base64,
					media_content_type: contentType,
				};
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

