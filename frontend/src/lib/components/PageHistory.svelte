<script lang="ts">
	import { api } from '$lib/api';
	import { onMount } from 'svelte';

	let { pageSlug, site } = $props<{ pageSlug: string; site: any }>();

	let revisions = $state<any[]>([]);
	let loading = $state(true);
	let viewingSource = $state<any>(null);
	let diffResult = $state('');
	let showDiff = $state(false);
	let selectedRevs = $state<number[]>([]);
	let historyError = $state('');

	onMount(async () => {
		await loadRevisions();
	});

	async function loadRevisions() {
		loading = true;
		try {
			const result = await api.getPageRevisions(pageSlug);
			revisions = Array.isArray(result) ? result : result.results || [];
		} catch { revisions = []; }
		loading = false;
	}

	async function viewSource(revNum: number) {
		try {
			viewingSource = await api.getPageSource(pageSlug, revNum);
		} catch (e: any) {
			historyError = e.message;
		}
	}

	async function viewDiff() {
		if (selectedRevs.length !== 2) {
			historyError = '请选择 2 个版本进行对比。';
			return;
		}
		const [a, b] = selectedRevs.sort((x, y) => x - y);
		try {
			const result = await api.ajaxModule('history/PageDiffModule', {
				page_unix_name: pageSlug,
				revision_a: a,
				revision_b: b,
			});
			diffResult = result.body || '';
			showDiff = true;
		} catch (e: any) {
			historyError = e.message;
		}
	}

	function toggleRev(revNum: number) {
		if (selectedRevs.includes(revNum)) {
			selectedRevs = selectedRevs.filter(r => r !== revNum);
		} else {
			if (selectedRevs.length >= 2) {
				selectedRevs = [selectedRevs[1], revNum];
			} else {
				selectedRevs = [...selectedRevs, revNum];
			}
		}
	}
</script>

<div id="page-title">历史记录：{pageSlug}</div>

{#if historyError}
	<div class="error-block" style="cursor:pointer" onclick={() => historyError = ''}>
		{historyError} <small>(点击关闭)</small>
	</div>
{/if}

{#if loading}
	<p>加载修订历史...</p>
{:else if viewingSource}
	<div style="margin-bottom: 1em;">
		<button class="btn" onclick={() => { viewingSource = null; }}>返回历史</button>
	</div>
	<h3>修订版本 {viewingSource.revision_number} — 源代码</h3>
	<pre style="background: #f8f8f8; border: 1px solid #ddd; padding: 1em; overflow-x: auto; font-size: 0.85em;">{viewingSource.source || '（空）'}</pre>
{:else if showDiff}
	<div style="margin-bottom: 1em;">
		<button class="btn" onclick={() => { showDiff = false; }}>返回历史</button>
	</div>
	<h3>对比：修订版本 {selectedRevs[0]} 与 {selectedRevs[1]}</h3>
	<div class="page-diff">
		{@html diffResult}
	</div>
{:else}
	<div style="margin-bottom: 1em;">
		<button class="btn btn-primary" onclick={viewDiff} disabled={selectedRevs.length !== 2}>对比所选</button>
		<span style="font-size:0.85em;color:#666;margin-left:0.5em">选择 2 个版本进行对比</span>
	</div>

	<table class="wiki-content-table" style="width: 100%;">
		<thead>
			<tr>
				<th style="width:30px"></th>
				<th style="width:50px">版本</th>
				<th>标记</th>
				<th>用户</th>
				<th>日期</th>
				<th>备注</th>
				<th>操作</th>
			</tr>
		</thead>
		<tbody>
			{#each revisions as rev}
				<tr>
					<td><input type="checkbox" checked={selectedRevs.includes(rev.revision_number)} onchange={() => toggleRev(rev.revision_number)}></td>
					<td>{rev.revision_number}</td>
					<td>
						{#if rev.flag_new}<span title="新建页面">N</span>{/if}
						{#if rev.flag_text}<span title="内容修改">S</span>{/if}
						{#if rev.flag_title}<span title="标题修改">T</span>{/if}
						{#if rev.flag_rename}<span title="重命名">R</span>{/if}
						{#if rev.flag_file}<span title="文件修改">F</span>{/if}
					</td>
					<td>{rev.user_string || rev.username || 'system'}</td>
					<td>{rev.date_last_edited ? new Date(rev.date_last_edited).toLocaleString() : ''}</td>
					<td>{rev.comments || ''}</td>
					<td>
						<a href="#" onclick={(e) => { e.preventDefault(); viewSource(rev.revision_number); }}>查看源码</a>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>

	{#if revisions.length === 0}
		<p>暂无修订历史。</p>
	{/if}
{/if}
