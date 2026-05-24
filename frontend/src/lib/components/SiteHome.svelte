<script lang="ts">
	import { api } from '$lib/api';

	let { user, onLogin, onLogout } = $props<{
		user: any;
		onLogin: (username: string, password: string) => void;
		onLogout: () => void;
	}>();

	let sites = $state<any[]>([]);
	let showLogin = $state(false);
	let showRegister = $state(false);

	let loginForm = $state({ username: '', password: '' });
	let registerForm = $state({ username: '', email: '', password: '', passwordConfirm: '' });
	let error = $state('');

	import { onMount } from 'svelte';

	onMount(async () => {
		try {
			const result = await api.listSites();
			sites = Array.isArray(result) ? result : result.results || [];
		} catch { sites = []; }
	});

	async function handleLogin() {
		error = '';
		try {
			await onLogin(loginForm.username, loginForm.password);
			showLogin = false;
		} catch (e: any) {
			error = e.message;
		}
	}

	async function handleRegister() {
		error = '';
		try {
			await api.register(registerForm.username, registerForm.email, registerForm.password, registerForm.passwordConfirm);
			await onLogin(registerForm.username, registerForm.password);
			showRegister = false;
		} catch (e: any) {
			error = e.message;
		}
	}
</script>

<div class="farm-page">
	<!-- Hero Header -->
	<header class="farm-header">
		<div class="farm-header-inner">
			<div class="farm-brand">
				<h1><a href="/">Folia</a></h1>
				<p class="farm-tagline">开源 Wiki 农场平台</p>
			</div>
			<nav class="farm-nav">
				{#if user}
					<span class="farm-user">{user.username}</span>
					<a href="/new-site" class="farm-nav-link">创建 Wiki</a>
					<a href="/account:settings" class="farm-nav-link">设置</a>
					<a href="#" class="farm-nav-link" onclick={(e) => { e.preventDefault(); onLogout(); }}>退出</a>
				{:else}
					<a href="#" class="farm-nav-link" onclick={(e) => { e.preventDefault(); showLogin = true; }}>登录</a>
					<a href="#" class="farm-nav-btn" onclick={(e) => { e.preventDefault(); showRegister = true; }}>注册</a>
				{/if}
			</nav>
		</div>
	</header>

	<!-- Hero Section -->
	<section class="farm-hero">
		<div class="farm-hero-inner">
			<h2>创建你自己的 Wiki</h2>
			<p>Folia 是免费、开源的 Wiki 托管平台。几秒钟即可搭建你的知识库、社区百科或项目文档。</p>
			{#if !user}
				<div class="farm-hero-actions">
					<button class="farm-btn-hero" onclick={() => showRegister = true}>免费注册</button>
					<a href="#sites" class="farm-btn-secondary">浏览 Wiki</a>
				</div>
			{:else}
				<div class="farm-hero-actions">
					<a href="/new-site" class="farm-btn-hero">创建新 Wiki</a>
					<a href="#sites" class="farm-btn-secondary">浏览 Wiki</a>
				</div>
			{/if}
		</div>
	</section>

	<!-- Features -->
	<section class="farm-features">
		<div class="farm-features-inner">
			<div class="feature-card">
				<div class="feature-icon">&#9997;</div>
				<h3>强大的标记语言</h3>
				<p>兼容 Wikidot 语法，支持模块、包含、条件等高级功能。</p>
			</div>
			<div class="feature-card">
				<div class="feature-icon">&#9734;</div>
				<h3>多人协作</h3>
				<p>完善的权限系统、论坛讨论、页面监视和通知。</p>
			</div>
			<div class="feature-card">
				<div class="feature-icon">&#9729;</div>
				<h3>独立子域名</h3>
				<p>每个 Wiki 拥有独立的子域名，支持自定义域名绑定。</p>
			</div>
		</div>
	</section>

	<!-- Sites List -->
	<section class="farm-sites" id="sites">
		<div class="farm-sites-inner">
			<h2>活跃 Wiki</h2>
			{#if sites.length === 0}
				<p class="empty-hint">还没有 Wiki，成为第一个创建者吧！</p>
			{:else}
				<div class="site-grid">
					{#each sites as s}
						<a href="http://{s.slug || s.unix_name}.brcnwiki.com" class="site-card">
							<div class="site-card-name">{s.name}</div>
							<div class="site-card-desc">{s.subtitle || s.description || '暂无描述'}</div>
							<div class="site-card-meta">{s.slug || s.unix_name}.brcnwiki.com</div>
						</a>
					{/each}
				</div>
			{/if}
		</div>
	</section>

	<!-- Footer -->
	<footer class="farm-footer">
		<p>Folia Wiki 农场 -- 开源 Wikidot 替代方案</p>
	</footer>

	<!-- Login Modal -->
	{#if showLogin}
		<div class="modal-overlay" onclick={() => { showLogin = false; error = ''; }}>
			<div class="modal-box" onclick={(e) => e.stopPropagation()}>
				<h3>登录</h3>
				{#if error}<p class="error-block">{error}</p>{/if}
				<form onsubmit={(e) => { e.preventDefault(); handleLogin(); }}>
					<div class="form-group"><label>用户名</label><input type="text" bind:value={loginForm.username}></div>
					<div class="form-group"><label>密码</label><input type="password" bind:value={loginForm.password}></div>
					<div class="modal-actions">
						<button type="submit" class="btn btn-primary">登录</button>
						<button type="button" class="btn" onclick={() => { showLogin = false; error = ''; }}>取消</button>
					</div>
				</form>
				<p class="modal-switch">没有账号？<a href="#" onclick={(e) => { e.preventDefault(); showLogin = false; showRegister = true; error = ''; }}>注册</a></p>
			</div>
		</div>
	{/if}

	<!-- Register Modal -->
	{#if showRegister}
		<div class="modal-overlay" onclick={() => { showRegister = false; error = ''; }}>
			<div class="modal-box" onclick={(e) => e.stopPropagation()}>
				<h3>注册账号</h3>
				{#if error}<p class="error-block">{error}</p>{/if}
				<form onsubmit={(e) => { e.preventDefault(); handleRegister(); }}>
					<div class="form-group"><label>用户名</label><input type="text" bind:value={registerForm.username}></div>
					<div class="form-group"><label>邮箱</label><input type="email" bind:value={registerForm.email}></div>
					<div class="form-group"><label>密码</label><input type="password" bind:value={registerForm.password}></div>
					<div class="form-group"><label>确认密码</label><input type="password" bind:value={registerForm.passwordConfirm}></div>
					<div class="modal-actions">
						<button type="submit" class="btn btn-primary">注册</button>
						<button type="button" class="btn" onclick={() => { showRegister = false; error = ''; }}>取消</button>
					</div>
				</form>
				<p class="modal-switch">已有账号？<a href="#" onclick={(e) => { e.preventDefault(); showRegister = false; showLogin = true; error = ''; }}>登录</a></p>
			</div>
		</div>
	{/if}
</div>

<style>
	.farm-page { min-height: 100vh; display: flex; flex-direction: column; background: #f5f5f8; }

	/* Header */
	.farm-header { background: linear-gradient(to right, #2a2a2a, #3d3d3d); padding: 0; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
	.farm-header-inner { max-width: 1100px; margin: 0 auto; padding: 0.8em 2em; display: flex; align-items: center; justify-content: space-between; }
	.farm-brand h1 { margin: 0; font-size: 1.8em; }
	.farm-brand h1 a { color: #fff; text-decoration: none; letter-spacing: 0.02em; }
	.farm-tagline { margin: 0; color: #aaa; font-size: 0.85em; }
	.farm-nav { display: flex; align-items: center; gap: 0.8em; }
	.farm-nav-link { color: #ccc; text-decoration: none; font-size: 0.9em; padding: 0.3em 0.5em; }
	.farm-nav-link:hover { color: #fff; text-decoration: none; }
	.farm-user { color: #eee; font-weight: bold; font-size: 0.9em; }
	.farm-nav-btn {
		color: #fff; background: #b01; padding: 0.4em 1em; border-radius: 3px;
		text-decoration: none; font-size: 0.9em; transition: background 0.15s;
	}
	.farm-nav-btn:hover { background: #c12; text-decoration: none; }

	/* Hero */
	.farm-hero { background: linear-gradient(135deg, #444 0%, #222 100%); color: #fff; padding: 3em 2em; text-align: center; }
	.farm-hero-inner { max-width: 700px; margin: 0 auto; }
	.farm-hero h2 { font-size: 2.2em; margin: 0 0 0.4em; font-weight: normal; }
	.farm-hero p { font-size: 1.1em; color: #ccc; margin: 0 0 1.5em; line-height: 1.5; }
	.farm-hero-actions { display: flex; gap: 1em; justify-content: center; }
	.farm-btn-hero {
		background: #b01; color: #fff; border: none; padding: 0.7em 2em;
		font-size: 1.1em; border-radius: 4px; cursor: pointer; text-decoration: none;
		transition: background 0.15s; display: inline-block;
	}
	.farm-btn-hero:hover { background: #c12; text-decoration: none; color: #fff; }
	.farm-btn-secondary {
		background: transparent; color: #ccc; border: 1px solid #666; padding: 0.7em 2em;
		font-size: 1.1em; border-radius: 4px; text-decoration: none; display: inline-block;
		transition: all 0.15s;
	}
	.farm-btn-secondary:hover { border-color: #999; color: #fff; text-decoration: none; }

	/* Features */
	.farm-features { padding: 2.5em 2em; background: #fff; }
	.farm-features-inner { max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: repeat(3, 1fr); gap: 2em; }
	.feature-card { text-align: center; padding: 1.5em; }
	.feature-icon { font-size: 2.5em; margin-bottom: 0.3em; }
	.feature-card h3 { margin: 0.3em 0; font-size: 1.1em; color: #333; }
	.feature-card p { color: #666; font-size: 0.9em; line-height: 1.5; margin: 0; }

	/* Sites */
	.farm-sites { padding: 2.5em 2em; flex: 1; }
	.farm-sites-inner { max-width: 1100px; margin: 0 auto; }
	.farm-sites h2 { margin: 0 0 1em; color: #333; font-size: 1.5em; border-bottom: 2px solid #ddd; padding-bottom: 0.3em; }
	.empty-hint { color: #888; font-style: italic; }
	.site-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.2em; }
	.site-card {
		display: block; background: #fff; border: 1px solid #ddd; border-radius: 4px;
		padding: 1.2em; text-decoration: none; transition: all 0.15s;
		box-shadow: 0 1px 3px rgba(0,0,0,0.05);
	}
	.site-card:hover { border-color: #b01; box-shadow: 0 3px 8px rgba(0,0,0,0.1); transform: translateY(-2px); text-decoration: none; }
	.site-card-name { font-weight: bold; color: #333; font-size: 1.1em; margin-bottom: 0.3em; }
	.site-card-desc { color: #666; font-size: 0.9em; margin-bottom: 0.6em; line-height: 1.4; }
	.site-card-meta { color: #999; font-size: 0.8em; }

	/* Footer */
	.farm-footer { background: #2a2a2a; color: #888; text-align: center; padding: 1.5em; font-size: 0.85em; }

	/* Modals */
	.modal-overlay {
		position: fixed; top: 0; left: 0; right: 0; bottom: 0;
		background: rgba(0,0,0,0.6); display: flex; align-items: center;
		justify-content: center; z-index: 1000;
	}
	.modal-box {
		background: #fff; padding: 2em; border-radius: 6px;
		min-width: 380px; max-width: 440px; box-shadow: 0 10px 40px rgba(0,0,0,0.3);
	}
	.modal-box h3 { margin: 0 0 1em; font-size: 1.3em; color: #333; }
	.modal-actions { margin-top: 1.2em; display: flex; gap: 0.5em; }
	.modal-switch { margin-top: 1em; font-size: 0.85em; color: #666; text-align: center; }
	.modal-switch a { color: #b01; }

	@media (max-width: 768px) {
		.farm-features-inner { grid-template-columns: 1fr; }
		.farm-hero h2 { font-size: 1.6em; }
		.farm-header-inner { flex-direction: column; gap: 0.5em; }
		.site-grid { grid-template-columns: 1fr; }
	}
</style>