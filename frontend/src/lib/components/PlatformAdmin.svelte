<script lang="ts">
	import { api } from '$lib/api';
	import { onMount } from 'svelte';

	type Tab = 'sites' | 'users' | 'stats';
	let tab = $state<Tab>('sites');
	let sites = $state<any[]>([]);
	let users = $state<any[]>([]);
	let stats = $state<any>(null);
	let loading = $state(true);
	let siteSearch = $state('');
	let userSearch = $state('');
	let adminError = $state('');

	onMount(async () => {
		await loadSites();
		loading = false;
	});

	async function loadSites() {
		try {
			const result = await api.platformListSites({ search: siteSearch });
			sites = result.results || [];
		} catch { sites = []; }
	}

	async function loadUsers() {
		try {
			const result = await api.platformListUsers({ search: userSearch });
			users = result.results || [];
		} catch { users = []; }
	}

	async function loadStats() {
		try { stats = await api.platformStats(); } catch {}
	}

	function switchTab(t: Tab) {
		tab = t;
		if (t === 'users') loadUsers();
		if (t === 'stats') loadStats();
	}

	async function suspendSite(siteId: number) {
		try { await api.platformSuspendSite(siteId); await loadSites(); }
		catch (e: any) { adminError = e.message; }
	}

	async function deleteSite(siteId: number) {
		if (!confirm('确定永久删除该站点？此操作不可撤销。')) return;
		try { await api.platformDeleteSite(siteId); await loadSites(); }
		catch (e: any) { adminError = e.message; }
	}

	async function banUser(userId: number) {
		const reason = prompt('封禁原因：') || '';
		try { await api.platformBanUser(userId, reason); await loadUsers(); }
		catch (e: any) { adminError = e.message; }
	}

	async function unbanUser(userId: number) {
		try { await api.platformUnbanUser(userId); await loadUsers(); }
		catch (e: any) { adminError = e.message; }
	}
</script>

<div id="page-title">平台管理</div>

{#if adminError}
	<div class="error-block" style="cursor:pointer" onclick={() => adminError = ''}>
		{adminError} <small>(点击关闭)</small>
	</div>
{/if}

{#if loading}
	<p>加载中...</p>
{:else}
	<div class="admin-tabs">
		<button class="tab-btn" class:active={tab === 'sites'} onclick={() => switchTab('sites')}>站点</button>
		<button class="tab-btn" class:active={tab === 'users'} onclick={() => switchTab('users')}>用户</button>
		<button class="tab-btn" class:active={tab === 'stats'} onclick={() => switchTab('stats')}>统计</button>
	</div>

	<div class="admin-content">
	{#if tab === 'sites'}
		<div class="search-bar">
			<input type="text" bind:value={siteSearch} placeholder="搜索站点..." onkeydown={(e) => { if (e.key === 'Enter') loadSites(); }}>
			<button class="btn" onclick={loadSites}>搜索</button>
		</div>
		<table class="wiki-content-table" style="width:100%">
			<thead><tr><th>标识</th><th>名称</th><th>成员数</th><th>创建时间</th><th>状态</th><th>操作</th></tr></thead>
			<tbody>
			{#each sites as s}
				<tr>
					<td><a href="http://{s.slug}.brcnwiki.com">{s.slug}</a></td>
					<td>{s.name}</td>
					<td>{s.member_count}</td>
					<td>{new Date(s.date_created).toLocaleDateString()}</td>
					<td>{s.suspended ? '已暂停' : '正常'}</td>
					<td>
						<button class="btn-sm" onclick={() => suspendSite(s.id)}>{s.suspended ? '恢复' : '暂停'}</button>
						<button class="btn-sm btn-danger" onclick={() => deleteSite(s.id)}>删除</button>
					</td>
				</tr>
			{/each}
			</tbody>
		</table>

	{:else if tab === 'users'}
		<div class="search-bar">
			<input type="text" bind:value={userSearch} placeholder="搜索用户..." onkeydown={(e) => { if (e.key === 'Enter') loadUsers(); }}>
			<button class="btn" onclick={loadUsers}>搜索</button>
		</div>
		<table class="wiki-content-table" style="width:100%">
			<thead><tr><th>用户名</th><th>邮箱</th><th>注册时间</th><th>状态</th><th>操作</th></tr></thead>
			<tbody>
			{#each users as u}
				<tr>
					<td>{u.username}</td>
					<td>{u.email}</td>
					<td>{new Date(u.date_joined).toLocaleDateString()}</td>
					<td>
						{#if u.banned}已封禁{:else if u.is_superuser}超级管理员{:else}正常{/if}
					</td>
					<td>
						{#if u.banned}
							<button class="btn-sm" onclick={() => unbanUser(u.id)}>解封</button>
						{:else}
							<button class="btn-sm btn-danger" onclick={() => banUser(u.id)}>封禁</button>
						{/if}
					</td>
				</tr>
			{/each}
			</tbody>
		</table>

	{:else if tab === 'stats'}
		{#if stats}
			<div class="stats-grid">
				<div class="stat-card"><div class="stat-num">{stats.total_sites}</div><div class="stat-label">站点总数</div></div>
				<div class="stat-card"><div class="stat-num">{stats.active_sites}</div><div class="stat-label">活跃站点</div></div>
				<div class="stat-card"><div class="stat-num">{stats.total_users}</div><div class="stat-label">用户总数</div></div>
				<div class="stat-card"><div class="stat-num">{stats.total_pages}</div><div class="stat-label">页面总数</div></div>
				<div class="stat-card"><div class="stat-num">{stats.banned_users}</div><div class="stat-label">已封禁用户</div></div>
			</div>
		{:else}
			<p>加载统计数据中...</p>
		{/if}
	{/if}
	</div>
{/if}

<style>
	.admin-tabs { border-bottom: 2px solid #688; margin-bottom: 1em; display: flex; gap: 2px; }
	.tab-btn { padding: 0.4em 1em; border: 1px solid #ccc; border-bottom: none; background: #f5f5f5; cursor: pointer; border-radius: 4px 4px 0 0; }
	.tab-btn.active { background: #688; color: #fff; border-color: #688; }
	.admin-content { max-width: 1000px; }
	.search-bar { display: flex; gap: 0.5em; margin-bottom: 1em; }
	.search-bar input { flex: 1; padding: 0.4em; border: 1px solid #ccc; border-radius: 3px; }
	.btn-sm { padding: 0.2em 0.5em; font-size: 0.85em; border: 1px solid #ccc; border-radius: 3px; background: #f9f9f9; cursor: pointer; }
	.btn-sm:hover { background: #eee; }
	.btn-danger { color: #c00; border-color: #c00; }
	.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1em; }
	.stat-card { text-align: center; padding: 1.5em; border: 1px solid #ddd; border-radius: 8px; background: #f9f9f9; }
	.stat-num { font-size: 2em; font-weight: bold; color: #688; }
	.stat-label { color: #666; margin-top: 0.3em; }
</style>