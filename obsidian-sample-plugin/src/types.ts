export type VaultEventType = "modify" | "create" | "delete" | "rename";

export interface GatewayLoginRequest {
	username: string;
	password: string;
}

export interface GatewayUserDto {
	id: number;
	username: string;
	email: string;
	first_name: string;
	last_name: string;
	user_role: string;
}

export interface GatewayLoginResponse {
	message: string;
	access_token: string;
	token_type: string;
	user: GatewayUserDto;
}

export interface GatewayFileEventPayload {
	event_type: VaultEventType;
	path: string;
	old_path?: string;
	content?: string;
	sha256?: string;
	timestamp: string;
	is_media?: boolean;
	media_content_base64?: string;
	media_content_type?: string;
}

