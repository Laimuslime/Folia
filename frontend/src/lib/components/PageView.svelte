<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { api } from '$lib/api';

	let { page, onEdit, onVote, onPageChange } = $props<{
		page: any;
		onEdit: () => void;
		onVote: (value: number) => void;
		onPageChange?: () => void;
	}>();

	let contentEl: HTMLElement;
	let optionsExpanded = $state(false);
	let showTagEditor = $state(false);
	let showRenameDialog = $state(false);
	let showDeleteDialog = $state(false);
	let showParentDialog = $state(false);
	let showBacklinks = $state(false);

	let editingTags = $state('');
	let renameSlug = $state('');
	let parentSlug = $state('');
	let backlinks = $state<any[]>([]);
	let watching = $state(false);
	let actionError = $state('');

	onMount(async () => {
		await tick();
		try {
			const result = await api.getWatchStatus(page.unix_name);
			watching = result.watching;
		} catch {}
	});

	async function toggleWatch() {
		try {
			if (watching) {
				await api.unwatchPage(page.unix_name);
				watching = false;
			} else {
				await api.watchPage(page.unix_name);
				watching = true;
			}
		} catch (e: any) { actionError = e.message; }
	}

	async function handleRename() {
		if (!renameSlug.trim()) return;
		try {
			await api.renamePage(page.unix_name, renameSlug.trim());
			showRenameDialog = false;
			window.location.href = '/' + renameSlug.trim();
		} catch (e: any) { actionError = e.message; }
	}

	async function handleDelete() {
		try {
			await api.deletePage(page.unix_name);
			showDeleteDialog = false;
			window.location.href = '/';
		} catch (e: any) { actionError = e.message; }
	}

	async function handleSetParent() {
		try {
			await api.setPageParent(page.unix_name, parentSlug.trim() || null);
			showParentDialog = false;
			onPageChange?.();
		} catch (e: any) { actionError = e.message; }
	}

	async function loadBacklinks() {
		try {
			backlinks = await api.getBacklinks(page.unix_name);
			showBacklinks = true;
		} catch (e: any) { actionError = e.message; }
	}

	async function toggleBlock() {
		try {
			if (page.blocked) {
				await api.unblockPage(page.unix_name);
			} else {
				await api.blockPage(page.unix_name);
			}
			onPageChange?.();
		} catch (e: any) { actionError = e.message; }
	}

	function openTagEditor() {
		editingTags = (page.tags || []).join(' ');
		showTagEditor = true;
	}

	async function saveTags() {
		try {
			const tags = editingTags.split(/\s+/).filter(Boolean).map((t: string) => t.toLowerCase());
			await api.editPage(page.unix_name, { tags });
			showTagEditor = false;
			onPageChange?.();
		} catch (e: any) { actionError = e.message; }
	}
</script>

<!-- Breadcrumbs -->
{#if page.breadcrumbs?.length}
	<div id="breadcrumbs">
		{#each page.breadcrumbs as crumb}
			<a href="/{crumb.slug}">{crumb.title}</a> &raquo;
		{/each}
	</div>
{/if}

<!-- Page Title -->
<div id="page-title">
	{page.title}
	{#if page.blocked}
		<span class="lock-icon" title="此页面已锁定">&#128274;</span>
	{/if}
</div>

<!-- Rating Widget -->
<div class="page-rate-widget-box">
	<span class="rate-points">
		rating:&nbsp;<span class="number">{page.rate >= 0 ? '+' : ''}{page.rate ?? 0}</span>
	</span>
	<span class="rateup btn btn-default">
		<a href="#" title="vote up" onclick={(e) => { e.preventDefault(); onVote(1); }}>+</a>
	</span>
	<span class="ratedown btn btn-default">
		<a href="#" title="vote down" onclick={(e) => { e.preventDefault(); onVote(-1); }}>-</a>
	</span>
	<span class="cancel btn btn-default">
		<a href="#" title="cancel vote" onclick={(e) => { e.preventDefault(); onVote(0); }}>x</a>
	</span>
</div>

<!-- Page Content -->
<div id="page-content" bind:this={contentEl}>
	{@html page.compiled_html || '<p><em>Empty page.</em></p>'}
</div>

<!-- Tags -->
{#if page.tags?.length && !showTagEditor}
	<div class="page-tags">
		<span>
			标签:
			{#each page.tags as tag}
				<a href="/system:page-tags/tag/{tag}">{tag}</a>
			{/each}
		</span>
	</div>
{/if}

<!-- Tag Editor -->
{#if showTagEditor}
	<div class="tag-editor">
		<label>标签（空格分隔）：</label>
		<input type="text" bind:value={editingTags} placeholder="tag1 tag2 tag3">
		<button class="btn btn-sm" onclick={saveTags}>保存</button>
		<button class="btn btn-sm" onclick={() => showTagEditor = false}>取消</button>
	</div>
{/if}

<!-- Page Info -->
<div id="page-info">
	修订版本: {page.revision_number ?? 0}, 最后编辑:
	{page.date_last_edited ? new Date(page.date_last_edited).toLocaleString() : '未知'}
</div>

<!-- Action Error -->
{#if actionError}
	<div class="error-block" style="cursor:pointer" onclick={() => actionError = ''}>
		{actionError} <small>(点击关闭)</small>
	</div>
{/if}

<!-- Page Options Bottom Bar -->
<div id="page-options-bottom">
	<a href="#" onclick={(e) => { e.preventDefault(); onEdit(); }}>编辑</a>
	<a href="#" onclick={(e) => { e.preventDefault(); openTagEditor(); }}>标签</a>
	<a href="/discuss/{page.unix_name}">讨论</a>
	<a href="/history/{page.unix_name}">历史</a>
	<a href="/files/{page.unix_name}">附件</a>
	<a href="/print/{page.unix_name}">打印</a>
	<a href="/source/{page.unix_name}">源代码</a>
	<a href="#" onclick={(e) => { e.preventDefault(); toggleWatch(); }}>{watching ? '取消监视' : '监视'}</a>
	<a href="#" class="options-toggle" onclick={(e) => { e.preventDefault(); optionsExpanded = !optionsExpanded; }}>{optionsExpanded ? '- 选项' : '+ 选项'}</a>
</div>

{#if optionsExpanded}
	<div id="page-options-expand">
		<a href="#" onclick={(e) => { e.preventDefault(); loadBacklinks(); }}>反向链接</a>
		<a href="#" onclick={(e) => { e.preventDefault(); parentSlug = page.parent_slug || ''; showParentDialog = true; }}>父页面</a>
		<a href="#" onclick={(e) => { e.preventDefault(); toggleBlock(); }}>{page.blocked ? '解锁' : '锁定'}</a>
		<a href="#" onclick={(e) => { e.preventDefault(); renameSlug = page.unix_name; showRenameDialog = true; }}>重命名</a>
		<a href="#" onclick={(e) => { e.preventDefault(); showDeleteDialog = true; }}>删除</a>
	</div>
{/if}

<!-- Backlinks Panel -->
{#if showBacklinks}
	<div class="action-panel">
		<h4>反向链接 <a href="#" onclick={(e) => { e.preventDefault(); showBacklinks = false; }}>[关闭]</a></h4>
		{#if backlinks.length === 0}
			<p>没有页面链接到此页面。</p>
		{:else}
			<ul>
				{#each backlinks as link}
					<li><a href="/{link.slug}">{link.title}</a></li>
				{/each}
			</ul>
		{/if}
	</div>
{/if}

<!-- Rename Dialog -->
{#if showRenameDialog}
	<div class="action-panel">
		<h4>重命名页面</h4>
		<div class="form-group">
			<label>新地址：</label>
			<input type="text" bind:value={renameSlug}>
		</div>
		<button class="btn btn-primary btn-sm" onclick={handleRename}>确认重命名</button>
		<button class="btn btn-sm" onclick={() => showRenameDialog = false}>取消</button>
	</div>
{/if}

<!-- Delete Dialog -->
{#if showDeleteDialog}
	<div class="action-panel">
		<h4>删除页面</h4>
		<p>确定要删除页面 <strong>{page.unix_name}</strong> 吗？此操作不可撤销。</p>
		<button class="btn btn-danger btn-sm" onclick={handleDelete}>确认删除</button>
		<button class="btn btn-sm" onclick={() => showDeleteDialog = false}>取消</button>
	</div>
{/if}

<!-- Parent Dialog -->
{#if showParentDialog}
	<div class="action-panel">
		<h4>设置父页面</h4>
		<div class="form-group">
			<label>父页面地址（留空清除）：</label>
			<input type="text" bind:value={parentSlug} placeholder="parent-page-slug">
		</div>
		<button class="btn btn-primary btn-sm" onclick={handleSetParent}>保存</button>
		<button class="btn btn-sm" onclick={() => showParentDialog = false}>取消</button>
	</div>
{/if}

<style>
	.lock-icon { font-size: 0.7em; vertical-align: middle; margin-left: 0.3em; }
	.tag-editor { margin: 0.5em 0; padding: 0.5em; background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px; }
	.tag-editor input { padding: 0.3em; margin: 0 0.3em; border: 1px solid #ccc; width: 60%; }
	.action-panel { margin: 0.8em 0; padding: 0.8em; background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; }
	.action-panel h4 { margin: 0 0 0.5em; }
	#page-options-expand { padding: 5px 0; border-top: 1px dashed #ccc; margin-top: 3px; }
	#page-options-expand a { margin-right: 1em; font-size: 0.85em; }
	.btn-sm { padding: 0.2em 0.6em; font-size: 0.85em; }
	.btn-danger { background: #d9534f; color: #fff; border-color: #d43f3a; }
</style>