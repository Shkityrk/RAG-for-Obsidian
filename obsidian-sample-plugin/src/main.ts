import { Notice, Plugin } from "obsidian";

import { GatewayClient } from "./api/gatewayClient";
import { DEFAULT_SETTINGS, type PluginSettings, SyncSettingTab } from "./settings";
import { VaultSyncService } from "./sync/vaultSyncService";

export default class VaultGatewaySyncPlugin extends Plugin {
	settings: PluginSettings = DEFAULT_SETTINGS;
	private gatewayClient!: GatewayClient;
	private syncService!: VaultSyncService;
	private statusBarText?: HTMLElement;

	async onload(): Promise<void> {
		await this.loadSettings();
		this.gatewayClient = new GatewayClient(() => this.settings.gatewayUrl);
		this.syncService = new VaultSyncService(this.app, this.gatewayClient, () => this.settings, () =>
			this.ensureAuthenticated(),
		);

		this.statusBarText = this.addStatusBarItem();
		this.updateStatusBar();

		this.addSettingTab(new SyncSettingTab(this.app, this));
		this.registerSyncCommands();
		this.syncService.attach(this);

		if (this.settings.autoLoginOnLoad) {
			await this.tryLoginWithNotice(false);
		}
	}

	onunload(): void {
		this.updateStatusBar("sync stopped");
	}

	async loadSettings(): Promise<void> {
		const loaded = (await this.loadData()) as Partial<PluginSettings> | null;
		this.settings = Object.assign({}, DEFAULT_SETTINGS, loaded ?? {});
	}

	async saveSettings(): Promise<void> {
		await this.saveData(this.settings);
		this.updateStatusBar();
	}

	private registerSyncCommands(): void {
		this.addCommand({
			id: "gateway-login",
			name: "Login to gateway",
			callback: async () => {
				await this.tryLoginWithNotice(true);
			},
		});
		this.addCommand({
			id: "gateway-logout",
			name: "Logout from gateway",
			callback: async () => {
				this.settings.accessToken = "";
				await this.saveSettings();
				new Notice("Gateway token cleared");
			},
		});
	}

	private async tryLoginWithNotice(showSuccessNotice: boolean): Promise<void> {
		try {
			await this.ensureAuthenticated();
			if (showSuccessNotice) {
				new Notice("Gateway authentication success");
			}
		} catch (error: unknown) {
			const message = error instanceof Error ? error.message : "Unknown auth error";
			new Notice(`Gateway auth failed: ${message}`);
		}
	}

	async ensureAuthenticated(): Promise<string> {
		if (this.settings.accessToken) {
			return this.settings.accessToken;
		}
		if (!this.settings.username || !this.settings.password) {
			throw new Error("Username or password is empty in plugin settings");
		}

		const auth = await this.gatewayClient.login({
			username: this.settings.username,
			password: this.settings.password,
		});
		this.settings.accessToken = auth.access_token;
		await this.saveSettings();
		return auth.access_token;
	}

	updateStatusBar(overrideText?: string): void {
		if (!this.statusBarText) {
			return;
		}
		if (overrideText) {
			this.statusBarText.setText(overrideText);
			return;
		}

		const state = this.settings.syncEnabled ? "on" : "off";
		const token = this.settings.accessToken ? "token" : "no-token";
		this.statusBarText.setText(`gateway sync: ${state} (${token})`);
	}
}
