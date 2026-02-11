import { requestUrl } from "obsidian";

import type {
	GatewayFileEventPayload,
	GatewayLoginRequest,
	GatewayLoginResponse,
} from "../types";

interface HttpErrorPayload {
	detail?: string;
	message?: string;
}

export class GatewayClient {
	constructor(private readonly getBaseUrl: () => string) {}

	async login(payload: GatewayLoginRequest): Promise<GatewayLoginResponse> {
		return this.postJson<GatewayLoginResponse>("/api/auth/login", payload);
	}

	async sendFileEvent(token: string, payload: GatewayFileEventPayload): Promise<void> {
		await this.postJson<unknown>("/api/files/events", payload, token);
	}

	private async postJson<TResponse>(
		path: string,
		payload: object,
		token?: string,
	): Promise<TResponse> {
		const headers: Record<string, string> = {
			"Content-Type": "application/json",
		};
		if (token) {
			headers.Authorization = `Bearer ${token}`;
		}

		const response = await requestUrl({
			url: `${this.getBaseUrl().replace(/\/+$/u, "")}${path}`,
			method: "POST",
			headers,
			body: JSON.stringify(payload),
		});
		if (response.status >= 400) {
			const errorBody = response.json as HttpErrorPayload | null;
			const detail = errorBody?.detail ?? errorBody?.message ?? response.text;
			throw new Error(`Gateway ${path} failed (${response.status}): ${detail}`);
		}
		return response.json as TResponse;
	}
}

