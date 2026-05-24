<script lang="ts">
	import { api } from '$lib/api';
	import { onMount } from 'svelte';

	let { username } = $props<{ username: string }>();

	let profile = $state<any>(null);
	let sites = $state<any[]>([]);
	let activity = $state<any[]>([]);
	let loading = $state(true);
	let activeTab = $state<'profile' | 'activity' | 'sites'>('profile');
	let sendingPM = $state(false);
	let pmForm = $state({ subject: '', body: '' });
	let pmError = $state('');
	let pmSuccess = $state(false);
	let currentUser = $state<any>(null);

	onMount(async () => {
		try {
			profile = await api.getUserProfile(username);
			sites = await api.getUserSites(username);
		} catch {}
		try {
			currentUser = await api.getProfile();
		} catch {}
		try {
			activity = await api.getUserActivity(username);
		} catch { activity = []; }
		loading = false;
	});

	function formatDate(dateStr: string) {
		if (!dateStr) return '—';
		const d = new Date(dateStr);
		return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`;
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
			sendingPM = false;
		} catch (e: any) {
			pmError = e.message || '发送失败';
		}
	}
</script>

{#if loading}
	<div id="page-content"><p>加载中...</p></div>
{:else if !profile}
	<div id="page-title">用户不存在</div>
	<div id="page-content"><p>用户 <strong>{username}</strong> 不存在或已被删除。</p></div>
{:else}
	<div id="page-title">
		{profile.display_name || username}
		<span class="user-subtitle">({username})</span>
	</div>

	<div id="page-content">
		<!-- User Card -->
		<div class="user-profile-card">
			<div class="user-profile-left">
				{#if profile.avatar}
					<img src={profile.avatar} alt="头像" class="user-avatar-large">
				{:else}
					<div class="user-avatar-large user-avatar-placeholder">
						{username[0].toUpperCase()}
					</div>
				{/if}
			</div>
			<div class="user-profile-right">
				<table class="user-info-table">
					<tbody>
						<tr>
							<td class="info-label">用户名</td>
							<td class="info-value">{username}</td>
						</tr>
						{#if profile.display_name}
						<tr>
							<td class="info-label">昵称</td>
							<td class="info-value">{profile.display_name}</td>
						</tr>
						{/if}
						<tr>
							<td class="info-label">注册时间</td>
							<td class="info-value">{formatDate(profile.created_at)}</td>
						</tr>
						<tr>
							<td class="info-label">Karma</td>
							<td class="info-value">
								<span class="karma-value">{profile.karma ?? 0}</span>
								<span class="karma-bar">
									{#each Array(5) as _, i}
										<span class="karma-dot" class:filled={(profile.karma ?? 0) > i * 20}></span>
									{/each}
								</span>
							</td>
						</tr>
						<tr>
							<td class="info-label">参与站点</td>
							<td class="info-value">{sites.length} 个</td>
						</tr>
						{#if profile.receive_pm !== false && currentUser && currentUser.username !== username}
						<tr>
							<td class="info-label">联系</td>
							<td class="info-value">
								<a href="#" onclick={(e) => { e.preventDefault(); sendingPM = !sendingPM; }}>发送私信</a>
							</td>
						</tr>
						{/if}
					</tbody>
				</table>
			</div>
		</div>

		{#if profile.bio}
		<div class="user-bio-section">
			<h3>关于我</h3>
			<div class="user-bio-content">{profile.bio}</div>
		</div>
		{/if}

		<!-- PM Form -->
		{#if sendingPM}
		<div class="pm-form-box">
			<h3>发送私信给 {username}</h3>
			{#if pmError}<div class="error-block">{pmError}</div>{/if}
			{#if pmSuccess}<div class="success-block">私信已发送。</div>{/if}
			<div class="form-group">
				<label>主题：</label>
				<input type="text" bind:value={pmForm.subject}>
			</div>
			<div class="form-group">
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
		<div class="profile-tabs">
			<ul class="yui-nav">
				<li class:active={activeTab === 'profile'}>
					<a href="#" onclick={(e) => { e.preventDefault(); activeTab = 'profile'; }}>资料</a>
				</li>
				<li class:active={activeTab === 'activity'}>
					<a href="#" onclick={(e) => { e.preventDefault(); activeTab = 'activity'; }}>最近活动</a>
				</li>
				<li class:active={activeTab === 'sites'}>
					<a href="#" onclick={(e) => { e.preventDefault(); activeTab = 'sites'; }}>参与站点 ({sites.length})</a>
				</li>
			</ul>
		</div>

		<!-- Tab Content -->
		<div class="profile-tab-content">
			{#if activeTab === 'profile'}
				<div class="profile-detail-section">
					<table class="wiki-content-table" style="width:100%">
						<tbody>
							<tr><td class="info-label">用户名</td><td>{username}</td></tr>
							<tr><td class="info-label">真实姓名</td><td>{profile.display_name || '（未设置）'}</td></tr>
							<tr><td class="info-label">注册日期</td><td>{formatDate(profile.created_at)}</td></tr>
							<tr><td class="info-label">Karma 等级</td><td>{profile.karma ?? 0}</td></tr>
							<tr><td class="info-label">接受私信</td><td>{profile.receive_pm !== false ? '是' : '否'}</td></tr>
						</tbody>
					</table>
				</div>
			{:else if activeTab === 'activity'}
				<div class="activity-section">
					{#if activity.length === 0}
						<p class="empty-state">暂无最近活动。</p>
					{:else}
						<table class="wiki-content-table" style="width:100%">
							<thead>
								<tr><th>时间</th><th>操作</th><th>页面</th><th>站点</th></tr>
							</thead>
							<tbody>
								{#each activity as act}
								<tr>
									<td class="time-col">{timeSince(act.date)}</td>
									<td>{act.type === 'edit' ? '编辑' : act.type === 'create' ? '创建' : act.type === 'comment' ? '评论' : act.type}</td>
									<td><a href="/{act.page_slug}">{act.page_title || act.page_slug}</a></td>
									<td>{act.site_name || ''}</td>
								</tr>
								{/each}
							</tbody>
						</table>
					{/if}
				</div>
			{:else if activeTab === 'sites'}
				<div class="sites-section">
					{#if sites.length === 0}
						<p class="empty-state">该用户尚未加入任何站点。</p>
					{:else}
						<table class="wiki-content-table" style="width:100%">
							<thead>
								<tr><th>站点名称</th><th>描述</th><th>角色</th></tr>
							</thead>
							<tbody>
								{#each sites as s}
								<tr>
									<td><a href="http://{s.slug}.brcnwiki.com">{s.name}</a></td>
									<td>{s.subtitle || s.description || ''}</td>
									<td>{s.role || '成员'}</td>
								</tr>
								{/each}
							</tbody>
						</table>
					{/if}
				</div>
			{/if}
		</div>
	</div>
{/if}

<style>
	.user-subtitle { font-size: 0.5em; color: #666; font-weight: normal; }
	.user-profile-card {
		display: flex;
		gap: 1.5em;
		padding: 1.2em;
		border: 1px solid #ddd;
		background: #f9f9f9;
		margin-bottom: 1.5em;
	}
	.user-profile-left { flex-shrink: 0; }
	.user-avatar-large {
		width: 100px;
		height: 100px;
		border-radius: 4px;
		object-fit: cover;
		border: 1px solid #ccc;
	}
	.user-avatar-placeholder {
		display: flex;
		align-items: center;
		justify-content: center;
		background: #688;
		color: #fff;
		font-size: 2.5em;
		font-weight: bold;
	}
	.user-profile-right { flex: 1; }
	.user-info-table { width: 100%; border-collapse: collapse; }
	.user-info-table td { padding: 0.3em 0.5em; border-bottom: 1px solid #eee; }
	.info-label { color: #555; font-weight: bold; width: 100px; white-space: nowrap; }
	.info-value { color: #333; }
	.karma-value { margin-right: 0.5em; }
	.karma-bar { display: inline-flex; gap: 2px; }
	.karma-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: #ddd;
		border: 1px solid #bbb;
		display: inline-block;
	}
	.karma-dot.filled { background: #688; border-color: #577; }
	.user-bio-section { margin: 1em 0 1.5em; }
	.user-bio-section h3 { margin: 0 0 0.5em; font-size: 110%; }
	.user-bio-content {
		padding: 0.8em;
		background: #fff;
		border: 1px solid #eee;
		border-radius: 3px;
		line-height: 1.5;
	}
	.pm-form-box {
		border: 1px solid #ccc;
		background: #fafafa;
		padding: 1em;
		margin: 1em 0;
	}
	.pm-form-box h3 { margin: 0 0 0.8em; font-size: 110%; }
	.pm-form-box .form-group { margin-bottom: 0.6em; }
	.pm-form-box label { display: block; font-weight: bold; margin-bottom: 0.2em; }
	.pm-form-box input[type="text"],
	.pm-form-box textarea {
		width: 100%;
		padding: 0.4em;
		border: 1px solid #ccc;
		font-size: 0.95em;
	}
	.success-block {
		border: 1px solid #090;
		background: #efe;
		padding: 0.5em 1em;
		color: #060;
		margin: 0.5em 0;
	}
	.profile-tabs { margin-top: 1.5em; }
	.profile-tabs .yui-nav {
		list-style: none;
		display: flex;
		margin: 0;
		padding: 0;
		border-bottom: 1px solid #ccc;
	}
	.profile-tabs .yui-nav li {
		padding: 0.5em 1.2em;
		cursor: pointer;
		border: 1px solid transparent;
		border-bottom: none;
		margin-bottom: -1px;
		font-size: 0.95em;
	}
	.profile-tabs .yui-nav li.active {
		border-color: #ccc;
		background: #fff;
		font-weight: bold;
		border-bottom-color: #fff;
	}
	.profile-tabs .yui-nav li a { text-decoration: none; color: inherit; }
	.profile-tab-content { padding: 1em 0; }
	.empty-state { color: #888; font-style: italic; }
	.time-col { white-space: nowrap; color: #666; font-size: 0.9em; }
	.profile-detail-section .info-label { width: 120px; }
</style>
