<script lang="ts">
	import { api } from '$lib/api';

	let step = $state(1);
	let checking = $state(false);
	let slugAvailable = $state<boolean | null>(null);
	let slugMessage = $state('');
	let creating = $state(false);
	let error = $state('');

	let form = $state({
		slug: '',
		name: '',
		subtitle: '',
		description: '',
		private: false,
		language: 'zh',
	});

	let slugTimer: any = null;

	function onSlugInput() {
		slugAvailable = null;
		slugMessage = '';
		if (slugTimer) clearTimeout(slugTimer);
		if (!form.slug) return;
		slugTimer = setTimeout(checkSlug, 500);
	}

	async function checkSlug() {
		if (!form.slug) return;
		checking = true;
		try {
			const result = await api.checkSlug(form.slug);
			slugAvailable = result.available;
			slugMessage = result.detail || '';
		} catch {
			slugAvailable = null;
		}
		checking = false;
	}

	function nextStep() {
		if (step === 1 && (!form.slug || slugAvailable === false)) return;
		if (step === 2 && !form.name) return;
		step++;
	}

	function prevStep() { if (step > 1) step--; }

	async function createSite() {
		creating = true;
		error = '';
		try {
			await api.createSite(form);
			window.location.href = `http://${form.slug}.brcnwiki.com`;
		} catch (e: any) {
			error = e.message;
			creating = false;
		}
	}
</script>

<div id="page-title">创建新 Wiki</div>

<div class="wizard">
	<div class="steps-indicator">
		{#each ['地址', '信息', '设置', '确认'] as label, i}
			<span class="step-dot" class:active={step === i + 1} class:done={step > i + 1}>{i + 1}. {label}</span>
		{/each}
	</div>

	{#if error}<div class="msg-error">{error}</div>{/if}

	{#if step === 1}
		<h3>选择 Wiki 地址</h3>
		<p style="color:#666">你的 Wiki 将位于 <strong>{form.slug || '___'}.brcnwiki.com</strong></p>
		<div class="form-group">
			<label>Wiki 地址（slug）：</label>
			<input type="text" bind:value={form.slug} oninput={onSlugInput} placeholder="my-wiki">
			{#if checking}
				<span class="slug-status checking">检查中...</span>
			{:else if slugAvailable === true}
				<span class="slug-status available">可用</span>
			{:else if slugAvailable === false}
				<span class="slug-status taken">{slugMessage}</span>
			{/if}
		</div>
		<p style="font-size:0.85em;color:#888">只能包含小写字母、数字和连字符，至少 3 个字符</p>

	{:else if step === 2}
		<h3>Wiki 基本信息</h3>
		<div class="form-group">
			<label>Wiki 名称：</label>
			<input type="text" bind:value={form.name} placeholder="我的百科">
		</div>
		<div class="form-group">
			<label>副标题（可选）：</label>
			<input type="text" bind:value={form.subtitle} placeholder="一句话描述">
		</div>
		<div class="form-group">
			<label>详细描述（可选）：</label>
			<textarea bind:value={form.description} rows="3" placeholder="这个 Wiki 是关于什么的..."></textarea>
		</div>

	{:else if step === 3}
		<h3>站点设置</h3>
		<div class="form-group">
			<label><input type="checkbox" bind:checked={form.private}> 私有 Wiki（仅成员可见）</label>
		</div>
		<div class="form-group">
			<label>语言：</label>
			<select bind:value={form.language}>
				<option value="zh">中文</option>
				<option value="en">English</option>
				<option value="ja">日本語</option>
				<option value="ko">한국어</option>
			</select>
		</div>

	{:else if step === 4}
		<h3>确认创建</h3>
		<div class="confirm-summary">
			<p><strong>地址：</strong>{form.slug}.brcnwiki.com</p>
			<p><strong>名称：</strong>{form.name}</p>
			{#if form.subtitle}<p><strong>副标题：</strong>{form.subtitle}</p>{/if}
			<p><strong>可见性：</strong>{form.private ? '私有' : '公开'}</p>
			<p><strong>语言：</strong>{form.language === 'zh' ? '中文' : form.language === 'en' ? 'English' : form.language}</p>
		</div>
	{/if}

	<div class="wizard-buttons">
		{#if step > 1}
			<button class="btn" onclick={prevStep}>上一步</button>
		{/if}
		{#if step < 4}
			<button class="btn btn-primary" onclick={nextStep} disabled={step === 1 && (!form.slug || slugAvailable !== true)}>下一步</button>
		{:else}
			<button class="btn btn-primary" onclick={createSite} disabled={creating}>{creating ? '创建中...' : '创建 Wiki'}</button>
		{/if}
	</div>
</div>

<style>
	.wizard { max-width: 600px; }
	.steps-indicator { display: flex; gap: 1em; margin-bottom: 1.5em; font-size: 0.9em; }
	.step-dot { color: #999; }
	.step-dot.active { color: #688; font-weight: bold; }
	.step-dot.done { color: #4caf50; }
	.form-group { margin-bottom: 0.8em; }
	.form-group label { display: block; font-weight: bold; margin-bottom: 0.2em; }
	.form-group input[type="text"], .form-group textarea, .form-group select { width: 100%; padding: 0.4em; border: 1px solid #ccc; border-radius: 3px; }
	.slug-status { margin-left: 0.5em; font-size: 0.85em; }
	.slug-status.checking { color: #999; }
	.slug-status.available { color: #4caf50; }
	.slug-status.taken { color: #e53935; }
	.wizard-buttons { margin-top: 1.5em; display: flex; gap: 0.5em; }
	.confirm-summary { background: #f9f9f9; border: 1px solid #ddd; padding: 1em; border-radius: 4px; }
	.confirm-summary p { margin: 0.3em 0; }
	.msg-error { padding: 0.5em; margin-bottom: 1em; background: #fce4ec; border: 1px solid #e53935; border-radius: 4px; color: #c00; }
</style>
