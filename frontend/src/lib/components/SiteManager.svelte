<script lang="ts">
	import { api } from '$lib/api';
	import { onMount } from 'svelte';

	let { site } = $props<{ site: any }>();

	type Tab = 'general' | 'security' | 'members' | 'permissions' | 'appearance' | 'navigation' | 'legal';
	let tab = $state<Tab>('general');
	let members = $state<any[]>([]);
	let applications = $state<any[]>([]);
	let siteSettings = $state<any>({});
	let categories = $state<any[]>([]);
	let themes = $state<any[]>([]);
	let licenses = $state<any[]>([]);
	let loading = $state(true);
	let saving = $state(false);
	let message = $state('');

	let generalForm = $state({ name: '', subtitle: '', description: '', default_page: 'start', language: 'en' });
	let securityForm = $state({ private: false, visible: true, allow_membership_by_apply: true, allow_membership_by_password: false, membership_password: '' });
	let appearanceForm = $state({ theme_id: null as number | null, custom_css: '' });
	let inviteForm = $state({ username: '', message: '' });

	const slug = () => site.slug || site.unix_name;

	onMount(async () => {
		generalForm = {
			name: site.name || '',
			subtitle: site.subtitle || '',
			description: site.description || '',
			default_page: site.default_page || 'start',
			language: site.language || 'en',
		};
		securityForm = {
			private: site.private || false,
			visible: site.visible !== false,
			allow_membership_by_apply: true,
			allow_membership_by_password: false,
			membership_password: '',
		};
		await loadSettings();
		await loadMembers();
		loading = false;
	});

	async function loadSettings() {
		try {
			siteSettings = await api.getSiteSettings(slug());
			appearanceForm.custom_css = siteSettings.custom_css || '';
			appearanceForm.theme_id = siteSettings.theme_id;
			securityForm.allow_membership_by_apply = siteSettings.allow_membership_by_apply ?? true;
			securityForm.allow_membership_by_password = siteSettings.allow_membership_by_password ?? false;
			securityForm.membership_password = siteSettings.membership_password || '';
		} catch {}
	}

	async function loadMembers() {
		try {
			const result = await api.getSiteMembers(slug());
			members = Array.isArray(result) ? result : result.results || [];
		} catch { members = []; }
	}

	async function loadApplications() {
		try { applications = await api.getSiteApplications(slug()); } catch { applications = []; }
	}

	async function loadCategories() {
		try { categories = await api.getCategoryPermissions(slug()); } catch { categories = []; }
	}

	async function loadThemes() {
		try { themes = await api.getThemes(slug()); } catch { themes = []; }
	}

	async function loadLicenses() {
		try { licenses = await api.getLicenses(slug()); } catch { licenses = []; }
	}

	function showMessage(msg: string) { message = msg; setTimeout(() => message = '', 3000); }

	async function saveGeneral() {
		saving = true;
		try {
			await api.updateSiteSettings(slug(), generalForm);
			showMessage('设置已保存');
		} catch (e: any) { showMessage(e.message); }
		saving = false;
	}

	async function saveSecurity() {
		saving = true;
		try {
			await api.updateSiteSettings(slug(), securityForm);
			showMessage('安全设置已保存');
		} catch (e: any) { showMessage(e.message); }
		saving = false;
	}

	async function saveAppearance() {
		saving = true;
		try {
			await api.updateSiteSettings(slug(), { custom_css: appearanceForm.custom_css, theme_id: appearanceForm.theme_id });
			showMessage('外观已保存');
		} catch (e: any) { showMessage(e.message); }
		saving = false;
	}

	async function removeMember(userId: number) {
		if (!confirm('确定移除该成员？')) return;
		await api.removeMember(slug(), userId);
		await loadMembers();
		showMessage('成员已移除');
	}

	async function promoteMember(userId: number, role: string) {
		await api.promoteMember(slug(), userId, role);
		await loadMembers();
		showMessage(`已升级为${role === 'admin' ? '管理员' : '版主'}`);
	}

	async function demoteMember(userId: number) {
		await api.demoteMember(slug(), userId);
		await loadMembers();
		showMessage('已降级为普通成员');
	}

	async function handleApp(appId: number, decision: string) {
		await api.handleApplication(slug(), appId, decision);
		await loadApplications();
		showMessage(decision === 'accept' ? '已通过申请' : '已拒绝申请');
	}

	async function sendInvite() {
		if (!inviteForm.username) return;
		try {
			await api.sendInvitation(slug(), inviteForm.username, inviteForm.message);
			inviteForm = { username: '', message: '' };
			showMessage('邀请已发送');
		} catch (e: any) { showMessage(e.message); }
	}

	async function savePermissions(catId: number, perms: Record<string, string>) {
		await api.updateCategoryPermissions(slug(), catId, perms);
		showMessage('权限已更新');
	}

	function switchTab(t: Tab) {
		tab = t;
		if (t === 'members') { loadApplications(); }
		if (t === 'permissions') { loadCategories(); }
		if (t === 'appearance') { loadThemes(); }
		if (t === 'legal') { loadLicenses(); }
	}
</script>

<div id="page-title">站点管理</div>

{#if loading}
	<p>加载中...</p>
{:else}
	<div class="admin-tabs">
		{#each [['general','常规'],['security','安全'],['members','成员'],['permissions','权限'],['appearance','外观'],['navigation','导航'],['legal','许可证']] as [key, label]}
			<button class="tab-btn" class:active={tab === key} onclick={() => switchTab(key as Tab)}>{label}</button>
		{/each}
	</div>

	{#if message}
		<div class="admin-message">{message}</div>
	{/if}

	<div class="admin-content">
	{#if tab === 'general'}
		<h3>常规设置</h3>
		<div class="form-group">
			<label>站点名称：</label>
			<input type="text" bind:value={generalForm.name}>
		</div>
		<div class="form-group">
			<label>副标题：</label>
			<input type="text" bind:value={generalForm.subtitle}>
		</div>
		<div class="form-group">
			<label>描述：</label>
			<textarea bind:value={generalForm.description} rows="4"></textarea>
		</div>
		<div class="form-group">
			<label>默认页面：</label>
			<input type="text" bind:value={generalForm.default_page}>
		</div>
		<div class="form-group">
			<label>语言：</label>
			<select bind:value={generalForm.language}>
				<option value="en">English</option>
				<option value="zh">中文</option>
				<option value="ja">日本語</option>
				<option value="ko">한국어</option>
			</select>
		</div>
		<button class="btn btn-primary" onclick={saveGeneral} disabled={saving}>{saving ? '保存中...' : '保存'}</button>

	{:else if tab === 'security'}
		<h3>安全与访问</h3>
		<div class="form-group">
			<label><input type="checkbox" bind:checked={securityForm.private}> 私有站点（仅成员可见）</label>
		</div>
		<div class="form-group">
			<label><input type="checkbox" bind:checked={securityForm.visible}> 在站点列表中可见</label>
		</div>
		<h4>成员加入方式</h4>
		<div class="form-group">
			<label><input type="checkbox" bind:checked={securityForm.allow_membership_by_apply}> 允许通过申请加入</label>
		</div>
		<div class="form-group">
			<label><input type="checkbox" bind:checked={securityForm.allow_membership_by_password}> 允许通过密码加入</label>
		</div>
		{#if securityForm.allow_membership_by_password}
			<div class="form-group">
				<label>密码：</label>
				<input type="text" bind:value={securityForm.membership_password}>
			</div>
		{/if}
		<button class="btn btn-primary" onclick={saveSecurity} disabled={saving}>{saving ? '保存中...' : '保存'}</button>

<!-- TEMPLATE_CONTINUED -->
	{:else if tab === 'members'}
		<h3>成员（{members.length}）</h3>
		<table class="wiki-content-table" style="width:100%">
			<thead><tr><th>用户名</th><th>加入时间</th><th>角色</th><th>操作</th></tr></thead>
			<tbody>
			{#each members as m}
				<tr>
					<td>{m.username}</td>
					<td>{m.date_joined ? new Date(m.date_joined).toLocaleDateString() : ''}</td>
					<td>{m.role === 'admin' ? '管理员' : m.role === 'moderator' ? '版主' : '成员'}</td>
					<td>
						{#if m.role === 'member'}
							<button class="btn-sm" onclick={() => promoteMember(m.user, 'moderator')}>升为版主</button>
							<button class="btn-sm" onclick={() => promoteMember(m.user, 'admin')}>升为管理员</button>
						{:else if m.role !== 'admin'}
							<button class="btn-sm" onclick={() => demoteMember(m.user)}>降级</button>
						{/if}
						<button class="btn-sm btn-danger" onclick={() => removeMember(m.user)}>移除</button>
					</td>
				</tr>
			{/each}
			</tbody>
		</table>

		<h4 style="margin-top:1.5em">邀请成员</h4>
		<div class="form-inline">
			<input type="text" bind:value={inviteForm.username} placeholder="用户名">
			<input type="text" bind:value={inviteForm.message} placeholder="附言（可选）">
			<button class="btn btn-primary" onclick={sendInvite}>发送邀请</button>
		</div>

		{#if applications.length > 0}
			<h4 style="margin-top:1.5em">待审核申请（{applications.length}）</h4>
			{#each applications as app}
				<div class="app-item">
					<strong>{app.username}</strong>：{app.text || '（无附言）'}
					<button class="btn-sm" onclick={() => handleApp(app.id, 'accept')}>通过</button>
					<button class="btn-sm" onclick={() => handleApp(app.id, 'decline')}>拒绝</button>
				</div>
			{/each}
		{/if}

	{:else if tab === 'permissions'}
		<h3>分类权限</h3>
		<p style="color:#666;font-size:0.9em">设置每个分类中各操作的权限。</p>
		{#if categories.length === 0}
			<p>加载分类中...</p>
		{:else}
			<table class="wiki-content-table" style="width:100%">
				<thead><tr><th>分类</th><th>编辑</th><th>创建</th><th>删除</th><th>移动</th><th>附件</th><th>评分</th><th></th></tr></thead>
				<tbody>
				{#each categories as cat}
					<tr>
						<td><strong>{cat.name}</strong></td>
						{#each ['edit','create','delete','move','attach','rate'] as action}
							<td>
								<select value={cat.permissions[action] || ''} onchange={(e) => cat.permissions[action] = (e.target as HTMLSelectElement).value}>
									<option value="">继承</option>
									<option value="a">所有人</option>
									<option value="r">注册用户</option>
									<option value="m">站点成员</option>
									<option value="o">管理员</option>
								</select>
							</td>
						{/each}
						<td><button class="btn-sm" onclick={() => savePermissions(cat.id, cat.permissions)}>保存</button></td>
					</tr>
				{/each}
				</tbody>
			</table>
		{/if}

	{:else if tab === 'appearance'}
		<h3>主题</h3>
		{#if themes.length > 0}
			<div class="form-group">
				<label>选择主题：</label>
				<select bind:value={appearanceForm.theme_id}>
					<option value={null}>默认</option>
					{#each themes as t}
						<option value={t.id}>{t.name}</option>
					{/each}
				</select>
			</div>
		{/if}
		<h3>自定义 CSS</h3>
		<textarea bind:value={appearanceForm.custom_css} rows="15" style="width:100%;font-family:monospace;font-size:0.85em"></textarea>
		<button class="btn btn-primary" onclick={saveAppearance} disabled={saving}>{saving ? '保存中...' : '保存'}</button>

	{:else if tab === 'navigation'}
		<h3>导航</h3>
		<p>编辑导航页面来自定义站点菜单。</p>
		<ul>
			<li><a href="/nav:top">编辑顶部导航（nav:top）</a></li>
			<li><a href="/nav:side">编辑侧边导航（nav:side）</a></li>
		</ul>

	{:else if tab === 'legal'}
		<h3>内容许可证</h3>
		<p style="color:#666;font-size:0.9em">选择本站内容的许可协议。</p>
		{#if licenses.length > 0}
			<div class="form-group">
				<select>
					<option value="">未指定许可证</option>
					{#each licenses as l}
						<option value={l.id}>{l.name}</option>
					{/each}
				</select>
			</div>
		{:else}
			<p>Creative Commons Attribution-ShareAlike 3.0 许可协议（默认）</p>
		{/if}
	{/if}
	</div>
{/if}

<style>
	.admin-tabs { border-bottom: 2px solid #688; margin-bottom: 1em; display: flex; flex-wrap: wrap; gap: 2px; }
	.tab-btn { padding: 0.4em 1em; border: 1px solid #ccc; border-bottom: none; background: #f5f5f5; cursor: pointer; border-radius: 4px 4px 0 0; }
	.tab-btn.active { background: #688; color: #fff; border-color: #688; }
	.admin-message { padding: 0.5em; margin-bottom: 1em; background: #e8f5e9; border: 1px solid #4caf50; border-radius: 4px; }
	.admin-content { max-width: 800px; }
	.form-group { margin-bottom: 0.8em; }
	.form-group label { display: block; font-weight: bold; margin-bottom: 0.2em; }
	.form-group input[type="text"], .form-group textarea, .form-group select { width: 100%; padding: 0.4em; border: 1px solid #ccc; border-radius: 3px; }
	.form-group input[type="checkbox"] { margin-right: 0.4em; }
	.form-inline { display: flex; gap: 0.5em; align-items: center; flex-wrap: wrap; }
	.form-inline input { padding: 0.4em; border: 1px solid #ccc; border-radius: 3px; }
	.btn-sm { padding: 0.2em 0.5em; font-size: 0.85em; border: 1px solid #ccc; border-radius: 3px; background: #f9f9f9; cursor: pointer; }
	.btn-sm:hover { background: #eee; }
	.btn-danger { color: #c00; border-color: #c00; }
	.btn-danger:hover { background: #fee; }
	.app-item { padding: 0.5em; margin-bottom: 0.5em; background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px; display: flex; align-items: center; gap: 0.5em; flex-wrap: wrap; }
	table select { padding: 0.2em; font-size: 0.85em; }
</style>