const API_BASE = import.meta.env.VITE_API_URL || '';

function formatApiError(err: any): string {
	if (typeof err === 'string') return err;
	if (err.detail) return err.detail;
	if (err.non_field_errors) return err.non_field_errors.join('; ');
	const fields = Object.keys(err).filter(k => Array.isArray(err[k]));
	if (fields.length > 0) {
		return fields.map(k => `${k}: ${err[k].join(', ')}`).join('; ');
	}
	return '请求失败';
}

class ApiClient {
	private baseUrl: string;
	private token: string | null = null;
	private refreshToken: string | null = null;
	private refreshing: Promise<boolean> | null = null;

	private getCookieDomain(): string {
		if (typeof window === 'undefined') return '';
		const host = window.location.hostname;
		const parts = host.split('.');
		if (parts.length >= 2) {
			return '.' + parts.slice(-2).join('.');
		}
		return host;
	}

	private setCookie(name: string, value: string, days: number) {
		const domain = this.getCookieDomain();
		const expires = new Date(Date.now() + days * 864e5).toUTCString();
		document.cookie = `${name}=${encodeURIComponent(value)};expires=${expires};path=/;domain=${domain};SameSite=Lax`;
	}

	private getCookie(name: string): string | null {
		const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
		return match ? decodeURIComponent(match[1]) : null;
	}

	private deleteCookie(name: string) {
		const domain = this.getCookieDomain();
		document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/;domain=${domain}`;
	}

	constructor(baseUrl: string) {
		this.baseUrl = `${baseUrl}/api/v1`;
		if (typeof window !== 'undefined') {
			this.token = this.getCookie('folia_token') || localStorage.getItem('folia_token');
			this.refreshToken = this.getCookie('folia_refresh') || localStorage.getItem('folia_refresh_token');
		}
	}

	setToken(token: string | null) {
		this.token = token;
		if (typeof window !== 'undefined') {
			if (token) {
				localStorage.setItem('folia_token', token);
				this.setCookie('folia_token', token, 1);
			} else {
				localStorage.removeItem('folia_token');
				this.deleteCookie('folia_token');
			}
		}
	}

	setRefreshToken(token: string | null) {
		this.refreshToken = token;
		if (typeof window !== 'undefined') {
			if (token) {
				localStorage.setItem('folia_refresh_token', token);
				this.setCookie('folia_refresh', token, 7);
			} else {
				localStorage.removeItem('folia_refresh_token');
				this.deleteCookie('folia_refresh');
			}
		}
	}

	isLoggedIn(): boolean {
		return !!this.token;
	}

	getToken(): string | null {
		return this.token;
	}

	private async tryRefresh(): Promise<boolean> {
		if (!this.refreshToken) return false;
		try {
			const response = await fetch(`${this.baseUrl}/auth/token/refresh/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ refresh: this.refreshToken }),
			});
			if (!response.ok) return false;
			const data = await response.json();
			this.setToken(data.access);
			return true;
		} catch {
			return false;
		}
	}

	private async request(path: string, options: RequestInit = {}): Promise<any> {
		const headers: Record<string, string> = {
			'Content-Type': 'application/json',
			...(options.headers as Record<string, string> || {}),
		};

		if (this.token) {
			headers['Authorization'] = `Bearer ${this.token}`;
		}

		const hostname = typeof window !== 'undefined' ? window.location.hostname : '';
		const parts = hostname.split('.');
		const siteSlug = (parts.length > 2 && parts[0] !== 'www') ? parts[0] : null;
		if (siteSlug) {
			headers['X-Site-Slug'] = siteSlug;
		}

		const response = await fetch(`${this.baseUrl}${path}`, {
			...options,
			headers,
		});

		if (!response.ok) {
			if (response.status === 301) {
				return response.json();
			}
			if (response.status === 401 && this.refreshToken && !path.includes('/auth/token')) {
				if (!this.refreshing) {
					this.refreshing = this.tryRefresh().finally(() => { this.refreshing = null; });
				}
				const refreshed = await this.refreshing;
				if (refreshed) {
					headers['Authorization'] = `Bearer ${this.token}`;
					const retry = await fetch(`${this.baseUrl}${path}`, { ...options, headers });
					if (retry.ok) {
						if (retry.status === 204) return null;
						return retry.json();
					}
					const retryErr = await retry.json().catch(() => ({ detail: retry.statusText }));
					throw new Error(formatApiError(retryErr));
				}
				this.setToken(null);
				this.setRefreshToken(null);
			}
			const error = await response.json().catch(() => ({ detail: response.statusText }));
			throw new Error(formatApiError(error));
		}

		if (response.status === 204) return null;
		return response.json();
	}

	// Auth
	async login(username: string, password: string) {
		const data = await this.request('/auth/token/', {
			method: 'POST',
			body: JSON.stringify({ username, password }),
		});
		this.setToken(data.access);
		this.setRefreshToken(data.refresh);
		return data;
	}

	async register(username: string, email: string, password: string, passwordConfirm: string) {
		return this.request('/auth/register/', {
			method: 'POST',
			body: JSON.stringify({ username, email, password, password_confirm: passwordConfirm }),
		});
	}

	async getProfile() {
		return this.request('/auth/profile/');
	}

	async updateProfile(data: { display_name?: string; bio?: string; language?: string; receive_pm?: boolean }) {
		return this.request('/auth/profile/', { method: 'PUT', body: JSON.stringify(data) });
	}

	async changePassword(oldPassword: string, newPassword: string) {
		return this.request('/auth/change-password/', {
			method: 'POST',
			body: JSON.stringify({ old_password: oldPassword, new_password: newPassword, new_password_confirm: newPassword }),
		});
	}

	async changeEmail(email: string) {
		return this.request('/auth/change-email/', { method: 'PUT', body: JSON.stringify({ email }) });
	}

	async uploadAvatar(file: File) {
		const formData = new FormData();
		formData.append('avatar', file);
		const headers: Record<string, string> = {};
		if (this.token) headers['Authorization'] = `Bearer ${this.token}`;
		const response = await fetch(`${this.baseUrl}/auth/avatar/`, { method: 'POST', headers, body: formData });
		if (!response.ok) {
			const error = await response.json().catch(() => ({ detail: response.statusText }));
			throw new Error(formatApiError(error));
		}
		return response.json();
	}

	async getUserProfile(username: string) {
		return this.request(`/users/${username}/`);
	}

	async getUserSites(username: string) {
		return this.request(`/users/${username}/sites/`);
	}

	async getUserActivity(username: string) {
		return this.request(`/users/${username}/activity/`);
	}

	async sendMessage(recipient: string, subject: string, body: string) {
		return this.request('/messages/', { method: 'POST', body: JSON.stringify({ recipient, subject, body }) });
	}

	async getMessages(folder: 'inbox' | 'sent' = 'inbox') {
		return this.request(`/messages/?folder=${folder}`);
	}

	async checkSlug(slug: string) {
		return this.request(`/sites/check-slug/?slug=${encodeURIComponent(slug)}`);
	}

	// Sites
	async listSites() {
		return this.request('/sites/');
	}

	async getSite(slug: string) {
		return this.request(`/sites/${slug}/`);
	}

	async createSite(data: { slug: string; name: string; subtitle?: string; description?: string; private?: boolean }) {
		return this.request('/sites/', { method: 'POST', body: JSON.stringify(data) });
	}

	// Pages
	async listPages(params?: { site?: string; tag?: string; category?: string }) {
		const query = new URLSearchParams(params as Record<string, string>).toString();
		return this.request(`/pages/?${query}`);
	}

	async getPage(slug: string) {
		return this.request(`/pages/${slug}/`);
	}

	async createPage(data: { slug: string; title: string; source: string; category?: string; tags?: string[] }) {
		return this.request('/pages/', { method: 'POST', body: JSON.stringify(data) });
	}

	async editPage(slug: string, data: { title?: string; source?: string; tags?: string[]; comment?: string }) {
		return this.request(`/pages/${slug}/`, { method: 'PUT', body: JSON.stringify(data) });
	}

	async deletePage(slug: string) {
		return this.request(`/pages/${slug}/`, { method: 'DELETE' });
	}

	async renamePage(slug: string, newSlug: string) {
		return this.request(`/pages/${slug}/rename/`, { method: 'POST', body: JSON.stringify({ new_slug: newSlug }) });
	}

	async movePage(slug: string, newCategory: string) {
		return this.request(`/pages/${slug}/move/`, { method: 'POST', body: JSON.stringify({ new_category: newCategory }) });
	}

	async blockPage(slug: string) {
		return this.request(`/pages/${slug}/block/`, { method: 'POST' });
	}

	async unblockPage(slug: string) {
		return this.request(`/pages/${slug}/block/`, { method: 'DELETE' });
	}

	async watchPage(slug: string) {
		return this.request(`/pages/${slug}/watch/`, { method: 'POST' });
	}

	async unwatchPage(slug: string) {
		return this.request(`/pages/${slug}/watch/`, { method: 'DELETE' });
	}

	async getWatchStatus(slug: string) {
		return this.request(`/pages/${slug}/watch/`);
	}

	async getBacklinks(slug: string) {
		return this.request(`/pages/${slug}/backlinks/`);
	}

	async setPageParent(slug: string, parentSlug: string | null) {
		if (parentSlug === null) {
			return this.request(`/pages/${slug}/parent/`, { method: 'DELETE' });
		}
		return this.request(`/pages/${slug}/parent/`, { method: 'POST', body: JSON.stringify({ parent_slug: parentSlug }) });
	}

	async getNotifications() {
		return this.request('/notifications/');
	}

	async getNotificationCount() {
		return this.request('/notifications/count/');
	}

	async markNotificationsRead(ids?: number[]) {
		return this.request('/notifications/read/', { method: 'POST', body: JSON.stringify({ ids }) });
	}

	async getPageRevisions(slug: string) {
		return this.request(`/pages/${slug}/revisions/`);
	}

	async votePage(slug: string, value: number) {
		return this.request(`/pages/${slug}/vote/`, { method: 'POST', body: JSON.stringify({ value }) });
	}

	// Forum
	async getForumGroups() {
		return this.request('/forum/groups/');
	}

	async getThreads(categoryId: number) {
		return this.request(`/forum/threads/?category=${categoryId}`);
	}

	async getThread(id: number) {
		return this.request(`/forum/threads/${id}/`);
	}

	async getThreadPosts(id: number) {
		return this.request(`/forum/threads/${id}/posts/`);
	}

	async createThread(categoryId: number, title: string, content: string) {
		return this.request('/forum/threads/', {
			method: 'POST',
			body: JSON.stringify({ category: categoryId, title, content }),
		});
	}

	async createPost(threadId: number, content: string, parentId?: number) {
		return this.request(`/forum/posts/`, {
			method: 'POST',
			body: JSON.stringify({ thread: threadId, text: content, parent: parentId }),
		});
	}

	// AJAX Module Connector
	async ajaxModule(moduleName: string, params: Record<string, any> = {}) {
		return this.request('/ajax-module-connector/', {
			method: 'POST',
			body: JSON.stringify({ moduleName, ...params }),
		});
	}

	// History
	async getPageSource(slug: string, revisionNumber?: number) {
		if (revisionNumber !== undefined) {
			return this.request(`/pages/${slug}/revisions/${revisionNumber}/`);
		}
		return this.request(`/pages/${slug}/revisions/`);
	}

	// Files
	async getPageFiles(slug: string) {
		return this.request(`/pages/${slug}/files/`);
	}

	async uploadFile(slug: string, file: File) {
		const formData = new FormData();
		formData.append('file', file);
		const headers: Record<string, string> = {};
		if (this.token) {
			headers['Authorization'] = `Bearer ${this.token}`;
		}
		const hostname = typeof window !== 'undefined' ? window.location.hostname : '';
		const parts = hostname.split('.');
		const siteSlug = (parts.length > 2 && parts[0] !== 'www') ? parts[0] : null;
		if (siteSlug) {
			headers['X-Site-Slug'] = siteSlug;
		}
		const response = await fetch(`${this.baseUrl}/pages/${slug}/files/`, {
			method: 'POST',
			headers,
			body: formData,
		});
		if (!response.ok) {
			const error = await response.json().catch(() => ({ detail: response.statusText }));
			throw new Error(formatApiError(error));
		}
		return response.json();
	}

	// Site management
	async getSiteMembers(slug: string) {
		return this.request(`/sites/${slug}/members/`);
	}

	async getSiteSettings(slug: string) {
		return this.request(`/sites/${slug}/settings/`);
	}

	async updateSiteSettings(slug: string, data: Record<string, any>) {
		return this.request(`/sites/${slug}/settings/`, { method: 'PUT', body: JSON.stringify(data) });
	}

	async removeMember(slug: string, userId: number) {
		return this.request(`/sites/${slug}/members/${userId}/remove/`, { method: 'POST' });
	}

	async promoteMember(slug: string, userId: number, role: string) {
		return this.request(`/sites/${slug}/members/${userId}/promote/`, { method: 'POST', body: JSON.stringify({ role }) });
	}

	async demoteMember(slug: string, userId: number) {
		return this.request(`/sites/${slug}/members/${userId}/demote/`, { method: 'POST' });
	}

	async getSiteApplications(slug: string) {
		return this.request(`/sites/${slug}/applications/`);
	}

	async handleApplication(slug: string, applicationId: number, decision: string, reply?: string) {
		return this.request(`/sites/${slug}/applications/`, { method: 'POST', body: JSON.stringify({ application_id: applicationId, decision, reply }) });
	}

	async getSiteInvitations(slug: string) {
		return this.request(`/sites/${slug}/invitations/`);
	}

	async sendInvitation(slug: string, username: string, message: string) {
		return this.request(`/sites/${slug}/invitations/`, { method: 'POST', body: JSON.stringify({ username, message }) });
	}

	async getSiteBlocks(slug: string) {
		return this.request(`/sites/${slug}/blocks/`);
	}

	async blockUser(slug: string, userId: number, reason: string) {
		return this.request(`/sites/${slug}/blocks/`, { method: 'POST', body: JSON.stringify({ user_id: userId, reason }) });
	}

	async unblockUser(slug: string, blockId: number) {
		return this.request(`/sites/${slug}/blocks/`, { method: 'DELETE', body: JSON.stringify({ block_id: blockId }) });
	}

	async getCategoryPermissions(slug: string) {
		return this.request(`/sites/${slug}/category-permissions/`);
	}

	async updateCategoryPermissions(slug: string, categoryId: number, permissions: Record<string, string>) {
		return this.request(`/sites/${slug}/category-permissions/`, { method: 'PUT', body: JSON.stringify({ category_id: categoryId, permissions }) });
	}

	async getThemes(slug: string) {
		return this.request(`/sites/${slug}/themes/`);
	}

	async getLicenses(slug: string) {
		return this.request(`/sites/${slug}/licenses/`);
	}

	// Platform admin
	async platformListSites(params?: { search?: string; page?: number }) {
		const query = new URLSearchParams(params as Record<string, string>).toString();
		return this.request(`/platform/sites/?${query}`);
	}

	async platformSuspendSite(siteId: number) {
		return this.request(`/platform/sites/${siteId}/suspend/`, { method: 'POST' });
	}

	async platformDeleteSite(siteId: number) {
		return this.request(`/platform/sites/${siteId}/`, { method: 'DELETE' });
	}

	async platformListUsers(params?: { search?: string; page?: number }) {
		const query = new URLSearchParams(params as Record<string, string>).toString();
		return this.request(`/platform/users/?${query}`);
	}

	async platformBanUser(userId: number, reason: string) {
		return this.request(`/platform/users/${userId}/ban/`, { method: 'POST', body: JSON.stringify({ reason }) });
	}

	async platformUnbanUser(userId: number) {
		return this.request(`/platform/users/${userId}/unban/`, { method: 'POST' });
	}

	async platformStats() {
		return this.request('/platform/stats/');
	}

	logout() {
		this.setToken(null);
		this.setRefreshToken(null);
	}
}

export const api = new ApiClient(API_BASE);
