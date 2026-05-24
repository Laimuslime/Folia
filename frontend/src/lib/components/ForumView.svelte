<script lang="ts">
	import { api } from '$lib/api';
	import { onMount } from 'svelte';

	let { site } = $props<{ site: any }>();

	let view = $state<'groups' | 'category' | 'thread' | 'new-thread'>('groups');
	let groups = $state<any[]>([]);
	let currentCategory = $state<any>(null);
	let threads = $state<any[]>([]);
	let currentThread = $state<any>(null);
	let posts = $state<any[]>([]);
	let loading = $state(true);

	let newThreadForm = $state({ title: '', description: '', content: '' });
	let replyForm = $state({ content: '', parentId: null as number | null });
	let showReply = $state(false);
	let forumError = $state('');

	onMount(async () => {
		await loadGroups();
	});

	async function loadGroups() {
		loading = true;
		try {
			const result = await api.getForumGroups();
			groups = Array.isArray(result) ? result : result.results || [];
		} catch { groups = []; }
		view = 'groups';
		loading = false;
	}

	async function openCategory(cat: any) {
		loading = true;
		currentCategory = cat;
		try {
			const result = await api.getThreads(cat.id);
			threads = Array.isArray(result) ? result : result.results || [];
		} catch { threads = []; }
		view = 'category';
		loading = false;
	}

	async function openThread(thread: any) {
		loading = true;
		currentThread = thread;
		try {
			const result = await api.getThreadPosts(thread.id);
			posts = Array.isArray(result) ? result : result.results || [];
		} catch { posts = []; }
		view = 'thread';
		loading = false;
	}

	async function submitThread() {
		if (!currentCategory) return;
		forumError = '';
		try {
			await api.createThread(currentCategory.id, newThreadForm.title, newThreadForm.content);
			newThreadForm = { title: '', description: '', content: '' };
			await openCategory(currentCategory);
		} catch (e: any) {
			forumError = e.message;
		}
	}

	async function submitReply() {
		if (!currentThread) return;
		forumError = '';
		try {
			await api.createPost(currentThread.id, replyForm.content, replyForm.parentId || undefined);
			replyForm = { content: '', parentId: null };
			showReply = false;
			await openThread(currentThread);
		} catch (e: any) {
			forumError = e.message;
		}
	}
</script>

<div id="page-title">
	{#if view === 'groups'}Forum{/if}
	{#if view === 'category'}{currentCategory?.name || 'Category'}{/if}
	{#if view === 'thread'}{currentThread?.title || 'Thread'}{/if}
	{#if view === 'new-thread'}New Thread{/if}
</div>

<!-- Breadcrumb -->
<div class="forum-breadcrumbs" style="margin-bottom: 1em; font-size: 0.9em;">
	<a href="#" onclick={(e) => { e.preventDefault(); loadGroups(); }}>论坛</a>
	{#if view !== 'groups'}
		&raquo; <a href="#" onclick={(e) => { e.preventDefault(); openCategory(currentCategory); }}>{currentCategory?.name}</a>
	{/if}
	{#if view === 'thread'}
		&raquo; {currentThread?.title}
	{/if}
</div>

{#if forumError}
	<div class="error-block" style="cursor:pointer" onclick={() => forumError = ''}>
		{forumError} <small>(点击关闭)</small>
	</div>
{/if}

{#if loading}
	<p>加载中...</p>
{:else if view === 'groups'}
	<!-- Forum Groups -->
	{#each groups as group}
		<div class="forum-group">
			<div class="head" style="background: #688; color: #fff; padding: 0.4em 0.8em; font-weight: bold;">
				{group.name}
			</div>
			{#if group.description}
				<div style="padding: 0.3em 0.8em; font-size: 0.85em; color: #666;">{group.description}</div>
			{/if}
			<table class="wiki-content-table" style="width: 100%;">
				<thead>
					<tr><th>分类</th><th style="width:80px">主题</th><th style="width:80px">帖子</th></tr>
				</thead>
				<tbody>
					{#each group.categories || [] as cat}
						<tr>
							<td>
								<a href="#" onclick={(e) => { e.preventDefault(); openCategory(cat); }}><strong>{cat.name}</strong></a>
								{#if cat.description}<br><span style="font-size:0.85em;color:#666">{cat.description}</span>{/if}
							</td>
							<td style="text-align:center">{cat.number_threads || 0}</td>
							<td style="text-align:center">{cat.number_posts || 0}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/each}

	{#if groups.length === 0}
		<p>论坛尚未设置分类。</p>
	{/if}

{:else if view === 'category'}
	<!-- Thread List -->
	<div style="margin-bottom: 1em;">
		<button class="btn btn-primary" onclick={() => { view = 'new-thread'; }}>发表新主题</button>
	</div>

	{#if threads.length === 0}
		<p>该分类下暂无主题。</p>
	{:else}
		<table class="wiki-content-table" style="width: 100%;">
			<thead>
				<tr><th>主题</th><th style="width:100px">发起人</th><th style="width:60px">帖子</th><th style="width:120px">日期</th></tr>
			</thead>
			<tbody>
				{#each threads as thread}
					<tr>
						<td>
							{#if thread.sticky}<span style="color:#900;font-weight:bold">[置顶]</span> {/if}
							<a href="#" onclick={(e) => { e.preventDefault(); openThread(thread); }}>{thread.title}</a>
							{#if thread.description}<br><span style="font-size:0.85em;color:#666">{thread.description}</span>{/if}
						</td>
						<td>{thread.username || thread.user_string || ''}</td>
						<td style="text-align:center">{thread.number_posts || 0}</td>
						<td>{thread.date_started ? new Date(thread.date_started).toLocaleDateString() : ''}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}

{:else if view === 'thread'}
	<!-- Thread Posts -->
	<div class="forum-thread-box">
		{#if currentThread?.description}
			<p style="color:#666;font-style:italic">{currentThread.description}</p>
		{/if}

		{#each posts as post, idx}
			<div class="post" style="border: 1px solid #ddd; margin-bottom: 1em; {idx === 0 ? '' : 'margin-left: ' + Math.min((post.parent ? 1 : 0) * 2, 6) + 'em;'}">
				<div class="head" style="background: #f0f0f0; padding: 0.4em 0.8em; font-size: 0.85em; border-bottom: 1px solid #ddd;">
					<strong>{post.username || post.user_string || '匿名'}</strong>
					<span style="float:right">{post.date_posted ? new Date(post.date_posted).toLocaleString() : ''}</span>
				</div>
				<div class="content" style="padding: 0.8em;">
					{#if post.title}<div style="font-weight:bold;margin-bottom:0.5em">{post.title}</div>{/if}
					<div>{@html post.text || ''}</div>
				</div>
				<div class="options" style="padding: 0.3em 0.8em; border-top: 1px solid #eee; font-size: 0.85em;">
					<a href="#" onclick={(e) => { e.preventDefault(); replyForm.parentId = post.id; showReply = true; }}>回复</a>
				</div>
			</div>
		{/each}

		{#if posts.length === 0}
			<p>暂无回复。</p>
		{/if}

		<!-- Reply form -->
		<div style="margin-top: 1em;">
			{#if !showReply}
				<button class="btn btn-primary" onclick={() => { showReply = true; replyForm.parentId = null; }}>发表回复</button>
			{:else}
				<div style="border: 1px solid #ccc; padding: 1em;">
					<h4>发表回复</h4>
					<textarea bind:value={replyForm.content} rows="6" style="width:100%;font-family:monospace"></textarea>
					<div style="margin-top: 0.5em;">
						<button class="btn btn-primary" onclick={submitReply}>提交</button>
						<button class="btn" onclick={() => { showReply = false; }}>取消</button>
					</div>
				</div>
			{/if}
		</div>
	</div>

{:else if view === 'new-thread'}
	<!-- New Thread Form -->
	<div style="border: 1px solid #ccc; padding: 1em;">
		<div style="margin-bottom: 0.8em;">
			<label style="display:block;font-weight:bold;margin-bottom:0.2em">标题：</label>
			<input type="text" bind:value={newThreadForm.title} style="width:100%;padding:0.3em">
		</div>
		<div style="margin-bottom: 0.8em;">
			<label style="display:block;font-weight:bold;margin-bottom:0.2em">描述（可选）：</label>
			<input type="text" bind:value={newThreadForm.description} style="width:100%;padding:0.3em">
		</div>
		<div style="margin-bottom: 0.8em;">
			<label style="display:block;font-weight:bold;margin-bottom:0.2em">内容：</label>
			<textarea bind:value={newThreadForm.content} rows="10" style="width:100%;font-family:monospace"></textarea>
		</div>
		<div>
			<button class="btn btn-primary" onclick={submitThread}>发表</button>
			<button class="btn" onclick={() => openCategory(currentCategory)}>取消</button>
		</div>
	</div>
{/if}
