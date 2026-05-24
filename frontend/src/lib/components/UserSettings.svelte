<script lang="ts">
	import { api } from '$lib/api';
	import { onMount } from 'svelte';

	type Tab = 'profile' | 'avatar' | 'email' | 'password' | 'notifications';
	let tab = $state<Tab>('profile');
	let loading = $state(true);
	let message = $state('');
	let error = $state('');

	let profileForm = $state({ display_name: '', bio: '', language: 'en' });
	let emailForm = $state({ email: '' });
	let passwordForm = $state({ old_password: '', new_password: '', new_password_confirm: '' });
	let notifForm = $state({ receive_pm: true });
	let avatarUrl = $state('');
	let avatarInput: HTMLInputElement;

	onMount(async () => {
		try {
			const profile = await api.getProfile();
			profileForm = { display_name: profile.display_name || '', bio: profile.bio || '', language: profile.language || 'en' };
			emailForm = { email: profile.email || '' };
			notifForm = { receive_pm: profile.receive_pm !== false };
			avatarUrl = profile.avatar || '';
		} catch {}
		loading = false;
	});

	function showMsg(msg: string) { message = msg; error = ''; setTimeout(() => message = '', 3000); }
	function showErr(msg: string) { error = msg; message = ''; setTimeout(() => error = '', 5000); }

	async function saveProfile() {
		try {
			await api.updateProfile(profileForm);
			showMsg('资料已保存');
		} catch (e: any) { showErr(e.message); }
	}

	async function saveEmail() {
		try {
			await api.changeEmail(emailForm.email);
			showMsg('邮箱已修改');
		} catch (e: any) { showErr(e.message); }
	}

	async function savePassword() {
		if (passwordForm.new_password !== passwordForm.new_password_confirm) {
			showErr('两次输入的密码不一致');
			return;
		}
		try {
			await api.changePassword(passwordForm.old_password, passwordForm.new_password);
			passwordForm = { old_password: '', new_password: '', new_password_confirm: '' };
			showMsg('密码已修改');
		} catch (e: any) { showErr(e.message); }
	}

	async function saveNotifications() {
		try {
			await api.updateProfile({ receive_pm: notifForm.receive_pm });
			showMsg('通知设置已保存');
		} catch (e: any) { showErr(e.message); }
	}

	async function handleAvatarUpload() {
		if (!avatarInput?.files?.length) return;
		try {
			const result = await api.uploadAvatar(avatarInput.files[0]);
			avatarUrl = result.avatar || '';
			showMsg('头像已更新');
		} catch (e: any) { showErr(e.message); }
	}
</script>

<div id="page-title">账号设置</div>

{#if loading}
	<p>加载中...</p>
{:else}
	<div class="admin-tabs">
		{#each [['profile','基本资料'],['avatar','头像'],['email','邮箱'],['password','密码'],['notifications','通知']] as [key, label]}
			<button class="tab-btn" class:active={tab === key} onclick={() => tab = key as Tab}>{label}</button>
		{/each}
	</div>

	{#if message}<div class="msg-success">{message}</div>{/if}
	{#if error}<div class="msg-error">{error}</div>{/if}

	<div class="settings-content">
	{#if tab === 'profile'}
		<h3>基本资料</h3>
		<div class="form-group">
			<label>显示名称：</label>
			<input type="text" bind:value={profileForm.display_name} placeholder="留空则显示用户名">
		</div>
		<div class="form-group">
			<label>个人简介：</label>
			<textarea bind:value={profileForm.bio} rows="4" placeholder="介绍一下自己..."></textarea>
		</div>
		<div class="form-group">
			<label>语言：</label>
			<select bind:value={profileForm.language}>
				<option value="en">English</option>
				<option value="zh">中文</option>
				<option value="ja">日本語</option>
				<option value="ko">한국어</option>
			</select>
		</div>
		<button class="btn btn-primary" onclick={saveProfile}>保存</button>

	{:else if tab === 'avatar'}
		<h3>头像</h3>
		<div class="avatar-section">
			{#if avatarUrl}
				<img src={avatarUrl} alt="当前头像" class="avatar-preview">
			{:else}
				<div class="avatar-placeholder">暂无头像</div>
			{/if}
			<div style="margin-top:1em">
				<input type="file" accept="image/*" bind:this={avatarInput}>
				<button class="btn btn-primary" onclick={handleAvatarUpload}>上传</button>
			</div>
			<p style="color:#666;font-size:0.85em;margin-top:0.5em">支持 JPG、PNG 格式，最大 2MB</p>
		</div>

	{:else if tab === 'email'}
		<h3>邮箱</h3>
		<div class="form-group">
			<label>邮箱地址：</label>
			<input type="email" bind:value={emailForm.email}>
		</div>
		<button class="btn btn-primary" onclick={saveEmail}>保存</button>

	{:else if tab === 'password'}
		<h3>修改密码</h3>
		<div class="form-group">
			<label>当前密码：</label>
			<input type="password" bind:value={passwordForm.old_password}>
		</div>
		<div class="form-group">
			<label>新密码：</label>
			<input type="password" bind:value={passwordForm.new_password}>
		</div>
		<div class="form-group">
			<label>确认新密码：</label>
			<input type="password" bind:value={passwordForm.new_password_confirm}>
		</div>
		<button class="btn btn-primary" onclick={savePassword}>修改密码</button>

	{:else if tab === 'notifications'}
		<h3>通知设置</h3>
		<div class="form-group">
			<label><input type="checkbox" bind:checked={notifForm.receive_pm}> 接收站内信</label>
		</div>
		<button class="btn btn-primary" onclick={saveNotifications}>保存</button>
	{/if}
	</div>
{/if}

<style>
	.admin-tabs { border-bottom: 2px solid #688; margin-bottom: 1em; display: flex; flex-wrap: wrap; gap: 2px; }
	.tab-btn { padding: 0.4em 1em; border: 1px solid #ccc; border-bottom: none; background: #f5f5f5; cursor: pointer; border-radius: 4px 4px 0 0; }
	.tab-btn.active { background: #688; color: #fff; border-color: #688; }
	.settings-content { max-width: 600px; }
	.form-group { margin-bottom: 0.8em; }
	.form-group label { display: block; font-weight: bold; margin-bottom: 0.2em; }
	.form-group input[type="text"], .form-group input[type="email"], .form-group input[type="password"], .form-group textarea, .form-group select { width: 100%; padding: 0.4em; border: 1px solid #ccc; border-radius: 3px; }
	.msg-success { padding: 0.5em; margin-bottom: 1em; background: #e8f5e9; border: 1px solid #4caf50; border-radius: 4px; }
	.msg-error { padding: 0.5em; margin-bottom: 1em; background: #fce4ec; border: 1px solid #e53935; border-radius: 4px; color: #c00; }
	.avatar-preview { width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 2px solid #ddd; }
	.avatar-placeholder { width: 120px; height: 120px; border-radius: 50%; background: #eee; display: flex; align-items: center; justify-content: center; color: #999; }
</style>
