<script lang="ts">
	import { api } from '$lib/api';
	import { onMount } from 'svelte';

	let { username } = $props<{ username: string }>();

	type Tab = 'profile' | 'member-of' | 'moderator-of' | 'admin-of' | 'contributions' | 'posts';

	let profile = $state<any>(null);
	let sites = $state<any[]>([]);
	let activity = $state<any[]>([]);
	let loading = $state(true);
	let activeTab = $state<Tab>('profile');
	let sendingPM = $state(false);
	let pmForm = $state({ subject: '', body: '' });
	let pmError = $state('');
	let pmSuccess = $state(false);
	let currentUser = $state<any>(null);
	let profileError = $state('');

	onMount(async () => {
		try {
			profile = await api.getUserProfile(username);
		} catch (e: any) {
			profileError = e.message || '加载用户信息失败';
			loading = false;
			return;
		}
		try { sites = await api.getUserSites(username); } catch { sites = []; }
		try { currentUser = await api.getProfile(); } catch {}
		try { activity = await api.getUserActivity(username); } catch { activity = []; }
		loading = false;
	});

	function formatDate(dateStr: string) {
		if (!dateStr) return '—';
		const d = new Date(dateStr);
		const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
		return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
	}

	function timeSince(dateStr: string) {
		const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
		if (seconds < 60) return '刚刚';
		const minutes = Math.floor(seconds / 60);
		if (minutes < 60) return `${minutes} 分钟前`;
		const hours = Math.floor(minutes / 60);
		if (hours < 24) return `${hours} 小时前`;
		const days = Math.floor(hours / 24);
		if (days < 30) return `${days} 天前`;
		return formatDate(dateStr);
	}

	function getKarmaLevel(karma: number): string {
		if (karma >= 100) return 'guru';
		if (karma >= 80) return 'very high';
		if (karma >= 60) return 'high';
		if (karma >= 40) return 'medium';
		if (karma >= 20) return 'low';
		return 'none';
	}

	function getKarmaFilledDots(karma: number): number {
		if (karma >= 100) return 5;
		if (karma >= 80) return 4;
		if (karma >= 60) return 3;
		if (karma >= 40) return 2;
		if (karma >= 20) return 1;
		return 0;
	}

	function getMemberSites() { return sites.filter(s => s.role === 'member' || !s.role); }
	function getModSites() { return sites.filter(s => s.role === 'moderator'); }
	function getAdminSites() { return sites.filter(s => s.role === 'admin'); }

	async function sendPM() {
		pmError = '';
		pmSuccess = false;
		if (!pmForm.subject.trim() || !pmForm.body.trim()) {
			pmError = '请填写主题和内容。';
			return;
		}
		try {
			await api.sendMessage(username, pmForm.subject, pmForm.body);
			pmSuccess = true;
			pmForm = { subject: '', body: '' };
		} catch (e: any) {
			pmError = e.message || '发送失败';
		}
	}
</script>

{#if loading}
	<div id="page-content"><p>加载中...</p></div>
{:else if profileError || !profile}
	<div id="page-title">用户不存在</div>
	<div id="page-content">
		<p>{profileError || `用户 ${username} 不存在或已被删除。`}</p>
	</div>
{:else}
	<div class="user-info-page">
		<!-- User Header -->
		<h1 class="profile-title">{profile.display_name || username}</h1>

		<!-- Action Links -->
		{#if currentUser && currentUser.username !== username}
			<div class="action-links">
				<a href="#" onclick={(e) => { e.preventDefault(); sendingPM = !sendingPM; }}>
					<img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%23666' viewBox='0 0 16 16'%3E%3Cpath d='M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V4zm2-1a1 1 0 0 0-1 1v.217l7 4.2 7-4.2V4a1 1 0 0 0-1-1H2zm13 2.383-4.708 2.825L15 11.105V5.383zm-.034 6.876-5.64-3.471L8 9.583l-1.326-.795-5.64 3.47A1 1 0 0 0 2 13h12a1 1 0 0 0 .966-.741zM1 11.105l4.708-2.897L1 5.383v5.722z'/%3E%3C/svg%3E" alt="">
					发送私信
				</a>
				<span class="sep">|</span>
				<a href="#" onclick={(e) => e.preventDefault()}>
					添加联系人
				</a>
			</div>
		{/if}

		<!-- PM Form -->
		{#if sendingPM}
			<div class="pm-panel">
				<h3>发送私信给 {username}</h3>
				{#if pmError}<div class="error-block">{pmError}</div>{/if}
				{#if pmSuccess}<div class="success-msg">私信已发送。</div>{/if}
				<div class="field">
					<label>主题：</label>
					<input type="text" bind:value={pmForm.subject}>
				</div>
				<div class="field">
					<label>内容：</label>
					<textarea bind:value={pmForm.body} rows="5"></textarea>
				</div>
				<div class="buttons">
					<button class="btn btn-primary" onclick={sendPM}>发送</button>
					<button class="btn" onclick={() => { sendingPM = false; }}>取消</button>
				</div>
			</div>
		{/if}

		<!-- Tabs -->
		<div class="yui-navset">
			<ul class="yui-nav">
				<li class:selected={activeTab === 'profile'}>
					<a href="#" onclick={(e) => { e.preventDefault(); activeTab = 'profile'; }}><em>资料</em></a>
				</li>
				<li class:selected={activeTab === 'member-of'}>
					<a href="#" onclick={(e) => { e.preventDefault(); activeTab = 'member-of'; }}><em>参与站点</em></a>
				</li>
				<li class:selected={activeTab === 'moderator-of'}>
					<a href="#" onclick={(e) => { e.preventDefault(); activeTab = 'moderator-of'; }}><em>版主</em></a>
				</li>
				<li class:selected={activeTab === 'admin-of'}>
					<a href="#" onclick={(e) => { e.preventDefault(); activeTab = 'admin-of'; }}><em>管理员</em></a>
				</li>
				<li class:selected={activeTab === 'contributions'}>
					<a href="#" onclick={(e) => { e.preventDefault(); activeTab = 'contributions'; }}><em>最近贡献</em></a>
				</li>
				<li class:selected={activeTab === 'posts'}>
					<a href="#" onclick={(e) => { e.preventDefault(); activeTab = 'posts'; }}><em>最近帖子</em></a>
				</li>
			</ul>

			<div class="yui-content">
				{#if activeTab === 'profile'}
					<div class="profile-box">
						<div class="profile-left">
							{#if profile.avatar}
								<img src={profile.avatar} alt="avatar" class="avatar-img">
							{:else}
								<div class="avatar-img avatar-placeholder">
									{username[0].toUpperCase()}
								</div>
							{/if}
						</div>
						<div class="profile-right">
							<dl class="profile-dl">
								<dt>真实姓名</dt>
								<dd>{profile.display_name || '（未设置）'}</dd>

								{#if profile.gender}
									<dt>性别</dt>
									<dd>{profile.gender === 'male' ? '男' : profile.gender === 'female' ? '女' : profile.gender}</dd>
								{/if}

								{#if profile.website}
									<dt>网站</dt>
									<dd><a href={profile.website} target="_blank" rel="noopener">{profile.website}</a></dd>
								{/if}

								<dt>注册时间</dt>
								<dd>{formatDate(profile.created_at || profile.date_joined)}</dd>

								<dt>账户类型</dt>
								<dd>free</dd>

								<dt>Karma</dt>
								<dd class="karma-cell">
									<span class="karma-level">{getKarmaLevel(profile.karma ?? 0)}</span>
									<span class="karma-dots">
										{#each Array(5) as _, i}
											<span class="karma-dot" class:filled={i < getKarmaFilledDots(profile.karma ?? 0)}></span>
										{/each}
									</span>
								</dd>
							</dl>
						</div>
					</div>

					{#if profile.bio}
						<div class="about-section">
							<h2>关于</h2>
							<p>{profile.bio}</p>
						</div>
					{/if}

				{:else if activeTab === 'member-of'}
					{#if getMemberSites().length === 0}
						<p class="empty">该用户尚未加入任何站点。</p>
					{:else}
						<table class="site-list-table">
							<tbody>
								{#each getMemberSites() as s}
									<tr>
										<td class="site-name"><a href="http://{s.slug}.brcnwiki.com">{s.name}</a></td>
										<td class="site-desc">{s.subtitle || s.description || ''}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					{/if}

				{:else if activeTab === 'moderator-of'}
					{#if getModSites().length === 0}
						<p class="empty">该用户不是任何站点的版主。</p>
					{:else}
						<table class="site-list-table">
							<tbody>
								{#each getModSites() as s}
									<tr>
										<td class="site-name"><a href="http://{s.slug}.brcnwiki.com">{s.name}</a></td>
										<td class="site-desc">{s.subtitle || s.description || ''}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					{/if}

				{:else if activeTab === 'admin-of'}
					{#if getAdminSites().length === 0}
						<p class="empty">该用户不是任何站点的管理员。</p>
					{:else}
						<table class="site-list-table">
							<tbody>
								{#each getAdminSites() as s}
									<tr>
										<td class="site-name"><a href="http://{s.slug}.brcnwiki.com">{s.name}</a></td>
										<td class="site-desc">{s.subtitle || s.description || ''}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					{/if}

				{:else if activeTab === 'contributions'}
					{#if activity.length === 0}
						<p class="empty">暂无最近贡献。</p>
					{:else}
						<table class="contrib-table">
							<thead>
								<tr><th>日期</th><th>操作</th><th>页面</th><th>站点</th></tr>
							</thead>
							<tbody>
								{#each activity as act}
									<tr>
										<td class="date-cell">{timeSince(act.date)}</td>
										<td>{act.type === 'edit' ? '编辑' : act.type === 'create' ? '新建' : act.type}</td>
										<td><a href="/{act.page_slug}">{act.page_title || act.page_slug}</a></td>
										<td>{act.site_name || ''}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					{/if}

				{:else if activeTab === 'posts'}
					<p class="empty">暂无最近帖子和评论。</p>
				{/if}
			</div>
		</div>
	</div>
{/if}

<style>
	.user-info-page { max-width: 900px; }
	.profile-title {
		font-size: 2em;
		font-weight: normal;
		margin: 0 0 0.3em;
		padding: 0 0 0.2em;
		border-bottom: 1px solid #ddd;
		color: #333;
	}
	.action-links {
		margin: 0.5em 0 1em;
		font-size: 0.9em;
	}
	.action-links a {
		color: #688;
		text-decoration: none;
	}
	.action-links a:hover { text-decoration: underline; }
	.action-links img { vertical-align: middle; margin-right: 3px; }
	.action-links .sep { color: #ccc; margin: 0 0.5em; }

	/* PM Panel */
	.pm-panel {
		border: 1px solid #ccc;
		background: #fafafa;
		padding: 1em;
		margin: 1em 0;
	}
	.pm-panel h3 { margin: 0 0 0.8em; font-size: 1.1em; }
	.pm-panel .field { margin-bottom: 0.6em; }
	.pm-panel label { display: block; font-weight: bold; margin-bottom: 0.2em; font-size: 0.9em; }
	.pm-panel input[type="text"],
	.pm-panel textarea { width: 100%; padding: 0.4em; border: 1px solid #ccc; font-size: 0.95em; }
	.pm-panel .buttons { margin-top: 0.5em; }
	.success-msg { color: #060; background: #efe; border: 1px solid #090; padding: 0.4em 0.8em; margin-bottom: 0.5em; }

	/* Tabs - Wikidot YUI style */
	.yui-navset { margin-top: 1.5em; }
	.yui-nav {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		border-bottom: 1px solid #999;
	}
	.yui-nav li {
		margin: 0 2px -1px 0;
	}
	.yui-nav li a {
		display: block;
		padding: 0.4em 1em;
		background: #e8e8e8;
		border: 1px solid #999;
		border-bottom: none;
		border-radius: 3px 3px 0 0;
		text-decoration: none;
		color: #555;
		font-size: 0.85em;
	}
	.yui-nav li a em { font-style: normal; }
	.yui-nav li.selected a {
		background: #fff;
		border-bottom: 1px solid #fff;
		color: #333;
		font-weight: bold;
	}
	.yui-nav li:not(.selected) a:hover {
		background: #f0f0f0;
	}
	.yui-content {
		border: 1px solid #999;
		border-top: none;
		padding: 1em;
		background: #fff;
	}

	/* Profile box */
	.profile-box {
		display: flex;
		gap: 1.5em;
	}
	.profile-left { flex-shrink: 0; }
	.avatar-img {
		width: 80px;
		height: 80px;
		border: 1px solid #ccc;
		object-fit: cover;
	}
	.avatar-placeholder {
		display: flex;
		align-items: center;
		justify-content: center;
		background: #688;
		color: #fff;
		font-size: 2em;
		font-weight: bold;
	}
	.profile-right { flex: 1; }

	/* Definition list */
	.profile-dl {
		margin: 0;
		display: grid;
		grid-template-columns: 100px 1fr;
		gap: 0.3em 1em;
		font-size: 0.92em;
	}
	.profile-dl dt {
		font-weight: bold;
		color: #555;
		text-align: right;
	}
	.profile-dl dd {
		margin: 0;
		color: #333;
	}

	/* Karma */
	.karma-cell { display: flex; align-items: center; gap: 0.5em; }
	.karma-level { font-style: italic; color: #555; }
	.karma-dots { display: inline-flex; gap: 2px; }
	.karma-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: #ddd;
		border: 1px solid #bbb;
		display: inline-block;
	}
	.karma-dot.filled { background: #390; border-color: #270; }

	/* About */
	.about-section { margin-top: 1.5em; }
	.about-section h2 { font-size: 1.1em; border-bottom: 1px solid #ddd; padding-bottom: 0.2em; }

	/* Tables */
	.site-list-table { width: 100%; border-collapse: collapse; }
	.site-list-table td { padding: 0.4em 0.5em; border-bottom: 1px solid #eee; }
	.site-list-table .site-name { font-weight: bold; white-space: nowrap; }
	.site-list-table .site-desc { color: #666; font-size: 0.9em; }

	.contrib-table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
	.contrib-table th { text-align: left; padding: 0.4em 0.5em; border-bottom: 2px solid #ddd; color: #555; font-size: 0.85em; }
	.contrib-table td { padding: 0.4em 0.5em; border-bottom: 1px solid #eee; }
	.contrib-table .date-cell { white-space: nowrap; color: #666; }

	.empty { color: #888; font-style: italic; }
</style>
