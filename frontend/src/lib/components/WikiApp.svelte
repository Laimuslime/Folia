<script lang="ts">
	import { api } from '$lib/api';
	import { onMount } from 'svelte';
	import PageView from '$lib/components/PageView.svelte';
	import PageEdit from '$lib/components/PageEdit.svelte';
	import SiteHome from '$lib/components/SiteHome.svelte';
	import ForumView from '$lib/components/ForumView.svelte';
	import PageHistory from '$lib/components/PageHistory.svelte';
	import FileManager from '$lib/components/FileManager.svelte';
	import SiteManager from '$lib/components/SiteManager.svelte';
	import PlatformAdmin from '$lib/components/PlatformAdmin.svelte';
	import UserSettings from '$lib/components/UserSettings.svelte';
	import UserProfile from '$lib/components/UserProfile.svelte';
	import CreateSite from '$lib/components/CreateSite.svelte';

	let site = $state<any>(null);
	let page = $state<any>(null);
	let user = $state<any>(null);
	let loading = $state(true);
	let mode = $state<'view' | 'edit' | 'history' | 'files' | 'forum' | 'manage' | 'platform' | 'source' | 'userinfo' | 'login' | 'register' | 'settings' | 'newsite'>('view');
	let sidebarHtml = $state('');
	let isFarmHome = $state(false);
	let currentPageSlug = $state('');
	let loginUsername = $state('');
	let loginPassword = $state('');
	let regForm = $state({ username: '', email: '', password: '', passwordConfirm: '' });
	let notifCount = $state(0);

	onMount(async () => {
		try {
			user = await api.getProfile();
			const nc = await api.getNotificationCount();
			notifCount = nc.unread || 0;
		} catch { /* not logged in */ }

		const hostname = window.location.hostname;
		const parts = hostname.split('.');
		const siteSlug = (parts.length > 2 && parts[0] !== 'www')
			? parts[0]
			: null;

		if (!siteSlug) {
			const path = window.location.pathname.slice(1);
			if (path === 'new-site') {
				mode = 'newsite';
			} else if (path === 'account:settings') {
				mode = 'settings';
			} else if (path.startsWith('user:info/') || path === 'user:info') {
				mode = 'userinfo';
				currentPageSlug = path.length > 10 ? path.slice(10) : '';
			} else {
				isFarmHome = true;
			}
			loading = false;
			return;
		}

		try {
			site = await api.getSite(siteSlug);
		} catch {
			loading = false;
			return;
		}

		const path = window.location.pathname.slice(1) || site.default_page || 'start';
		currentPageSlug = path;

		// Route based on path prefix
		if (path === 'forum:start' || path.startsWith('forum:')) {
			mode = 'forum';
			loading = false;
			return;
		}
		if (path.startsWith('history/')) {
			currentPageSlug = path.slice(8);
			mode = 'history';
			loading = false;
			return;
		}
		if (path.startsWith('files/')) {
			currentPageSlug = path.slice(6);
			mode = 'files';
			loading = false;
			return;
		}
		if (path.startsWith('source/')) {
			currentPageSlug = path.slice(7);
			mode = 'source';
		}
		if (path === 'admin:panel') {
			mode = 'platform';
			loading = false;
			return;
		}
		if (path === 'admin:manage' || path.startsWith('admin:')) {
			mode = 'manage';
			loading = false;
			return;
		}
		if (path.startsWith('user:info/') || path === 'user:info') {
			mode = 'userinfo';
			currentPageSlug = path.slice(10);
			loading = false;
			return;
		}
		if (path === 'auth:login') {
			mode = 'login';
			loading = false;
			return;
		}
		if (path === 'auth:register') {
			mode = 'register';
			loading = false;
			return;
		}
		if (path === 'account:settings') {
			mode = 'settings';
			loading = false;
			return;
		}
		if (path === 'new-site') {
			mode = 'newsite';
			loading = false;
			return;
		}

		// Load page
		try {
			const result = await api.getPage(currentPageSlug);
			if (result?.redirect) {
				currentPageSlug = result.redirect;
				page = await api.getPage(currentPageSlug);
				window.history.replaceState({}, '', '/' + currentPageSlug);
			} else {
				page = result;
			}
		} catch {
			page = null;
		}

		// Load sidebar
		try {
			const sidebar = await api.getPage('nav:side');
			sidebarHtml = sidebar?.compiled_html || '';
		} catch {
			sidebarHtml = '<ul><li><a href="/">Main</a></li><li><a href="/system:list-all-pages">All Pages</a></li></ul>';
		}

		loading = false;
	});

	function startEdit() { mode = 'edit'; }
	function cancelEdit() { mode = 'view'; }

	async function reloadPage() {
		try {
			page = await api.getPage(currentPageSlug);
		} catch { page = null; }
	}

	async function savePage(event: CustomEvent<{title: string; source: string; comment: string}>) {
		const { title, source, comment } = event.detail;
		if (page) {
			page = await api.editPage(page.unix_name, { title, source, comment });
		} else {
			page = await api.createPage({ slug: currentPageSlug, title, source });
		}
		mode = 'view';
	}

	async function vote(value: number) {
		if (!page) return;
		const result = await api.votePage(page.unix_name, value);
		page = { ...page, rate: result.rating };
	}

	async function login(username: string, password: string) {
		await api.login(username, password);
		user = await api.getProfile();
		if (mode === 'login') {
			window.location.href = '/';
		}
	}

	function logout() {
		api.logout();
		user = null;
	}

	async function handleRegister() {
		await api.register(regForm.username, regForm.email, regForm.password, regForm.passwordConfirm);
		await login(regForm.username, regForm.password);
	}
</script>


{#if loading}
	<div style="padding: 2em; text-align: center;">加载中...</div>
{:else if mode === 'newsite' && !site}
	<div style="padding: 2em; max-width: 700px; margin: 0 auto;">
		<CreateSite />
	</div>
{:else if mode === 'settings' && !site}
	<div style="padding: 2em; max-width: 700px; margin: 0 auto;">
		<UserSettings />
	</div>
{:else if mode === 'userinfo' && !site}
	<div style="padding: 2em; max-width: 700px; margin: 0 auto;">
		<UserProfile username={currentPageSlug} />
	</div>
{:else if isFarmHome}
	<SiteHome {user} onLogin={login} onLogout={logout} />
{:else if site}
	<!-- Login Status -->
	<div id="login-status">
		{#if user}
			<span><a href="/user:info/{user.username}">{user.username}</a></span>
			{#if notifCount > 0}
				<a href="#" class="notif-bell" title="通知">({notifCount})</a>
			{/if}
			<a href="/account:settings">设置</a>
			<a href="#" onclick={(e) => { e.preventDefault(); logout(); }}>退出</a>
		{:else}
			<a href="/auth:login">登录</a> | <a href="/auth:register">注册</a>
		{/if}
	</div>

	<!-- Search -->
	<div id="search-top-box">
		<form action="/search:site" method="get">
			<input type="text" name="q" placeholder="搜索本站" class="empty">
		</form>
	</div>

	<!-- Header -->
	<div id="header">
		<h1><a href="/">{site.name}</a></h1>
		{#if site.subtitle}
			<h2>{site.subtitle}</h2>
		{/if}
	</div>

	<!-- Top Bar -->
	<div id="top-bar">
		<ul>
			<li><a href="/">首页</a></li>
			<li><a href="/system:recent-changes">最近更改</a></li>
			<li><a href="/forum:start">论坛</a></li>
			<li><a href="/system:members">成员</a></li>
			<li><a href="/system:list-all-pages">所有页面</a></li>
			{#if user}
				<li><a href="/admin:manage">管理</a></li>
			{/if}
		</ul>
	</div>

	<!-- Content -->
	<div id="content-wrap">
		<div id="side-bar">
			{@html sidebarHtml}
		</div>

		<div id="main-content">
			{#if mode === 'forum'}
				<ForumView {site} />
			{:else if mode === 'platform'}
				<PlatformAdmin />
			{:else if mode === 'history'}
				<PageHistory pageSlug={currentPageSlug} {site} />
			{:else if mode === 'files'}
				<FileManager pageSlug={currentPageSlug} {site} />
			{:else if mode === 'manage'}
				<SiteManager {site} />
			{:else if mode === 'edit'}
				<PageEdit
					title={page?.title || ''}
					source={page?.current_source || ''}
					onSave={savePage}
					onCancel={cancelEdit}
				/>
			{:else if mode === 'source'}
				<div id="page-title">源代码：{currentPageSlug}</div>
				<pre style="background: #f8f8f8; border: 1px solid #ddd; padding: 1em; overflow-x: auto; font-size: 0.85em;">{page?.current_source || '（空）'}</pre>
			{:else if mode === 'userinfo'}
				<UserProfile username={currentPageSlug} />
			{:else if mode === 'settings'}
				<UserSettings />
			{:else if mode === 'newsite'}
				<CreateSite />
			{:else if mode === 'login'}
				<div id="page-title">登录</div>
				<div id="page-content">
					<form onsubmit={(e) => { e.preventDefault(); login(loginUsername, loginPassword); }}>
						<div class="form-group"><label>用户名：</label><input type="text" bind:value={loginUsername}></div>
						<div class="form-group"><label>密码：</label><input type="password" bind:value={loginPassword}></div>
						<button class="btn btn-primary" type="submit">登录</button>
					</form>
				</div>
			{:else if mode === 'register'}
				<div id="page-title">注册</div>
				<div id="page-content">
					<form onsubmit={(e) => { e.preventDefault(); handleRegister(); }}>
						<div class="form-group"><label>用户名：</label><input type="text" bind:value={regForm.username}></div>
						<div class="form-group"><label>邮箱：</label><input type="email" bind:value={regForm.email}></div>
						<div class="form-group"><label>密码：</label><input type="password" bind:value={regForm.password}></div>
						<div class="form-group"><label>确认密码：</label><input type="password" bind:value={regForm.passwordConfirm}></div>
						<button class="btn btn-primary" type="submit">注册</button>
					</form>
				</div>
			{:else if page}
				<PageView {page} onEdit={startEdit} onVote={vote} onPageChange={reloadPage} />
			{:else}
				<div id="page-title">页面不存在</div>
				<div id="page-content">
					<p>你要访问的页面 <strong>{currentPageSlug}</strong> 不存在。</p>
					{#if user}
						<p><a href="#" onclick={(e) => { e.preventDefault(); startEdit(); }}>创建此页面</a></p>
					{/if}
				</div>
				<div id="page-options-bottom">
					{#if user}
						<a href="#" onclick={(e) => { e.preventDefault(); startEdit(); }}>创建</a>
					{/if}
					<a href="/history/{currentPageSlug}">历史</a>
					<a href="/files/{currentPageSlug}">附件</a>
				</div>
			{/if}
		</div>
	</div>

	<!-- Footer -->
	<div id="footer">
		<div class="options">
			<a href="/system:recent-changes">最近更改</a> |
			<a href="/system:list-all-pages">所有页面</a>
		</div>
		<div id="license-area">
			由 <a href="http://www.brcnwiki.com">Folia Wiki 农场</a> 提供支持
		</div>
	</div>
{:else}
	<div style="padding: 2em;">
		<h1>站点不存在</h1>
		<p>你请求的 Wiki 站点不存在。</p>
		<p><a href="http://www.brcnwiki.com">返回 Folia 首页</a></p>
	</div>
{/if}
