<script lang="ts">
	import { api } from '$lib/api';
	import { onMount } from 'svelte';

	let { pageSlug, site } = $props<{ pageSlug: string; site: any }>();

	let files = $state<any[]>([]);
	let loading = $state(true);
	let uploading = $state(false);
	let fileInput: HTMLInputElement;
	let fileError = $state('');

	onMount(async () => {
		await loadFiles();
	});

	async function loadFiles() {
		loading = true;
		try {
			const result = await api.getPageFiles(pageSlug);
			files = Array.isArray(result) ? result : result.results || [];
		} catch { files = []; }
		loading = false;
	}

	async function handleUpload() {
		if (!fileInput?.files?.length) return;
		uploading = true;
		fileError = '';
		try {
			for (const file of fileInput.files) {
				await api.uploadFile(pageSlug, file);
			}
			fileInput.value = '';
			await loadFiles();
		} catch (e: any) {
			fileError = e.message;
		}
		uploading = false;
	}

	function formatSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / 1048576).toFixed(1)} MB`;
	}
</script>

<div id="page-title">文件：{pageSlug}</div>

{#if fileError}
	<div class="error-block" style="cursor:pointer" onclick={() => fileError = ''}>
		{fileError} <small>(点击关闭)</small>
	</div>
{/if}

{#if loading}
	<p>加载文件...</p>
{:else}
	<!-- Upload -->
	<div style="margin-bottom: 1em; padding: 1em; border: 1px solid #ddd; background: #f9f9f9;">
		<strong>上传文件</strong>
		<div style="margin-top: 0.5em;">
			<input type="file" bind:this={fileInput} multiple>
			<button class="btn btn-primary" onclick={handleUpload} disabled={uploading}>
				{uploading ? '上传中...' : '上传'}
			</button>
		</div>
	</div>

	<!-- File list -->
	{#if files.length === 0}
		<p>该页面暂无附件。</p>
	{:else}
		<table class="wiki-content-table" style="width: 100%;">
			<thead>
				<tr>
					<th>文件名</th>
					<th style="width:80px">大小</th>
					<th style="width:120px">类型</th>
					<th style="width:150px">上传时间</th>
					<th style="width:100px">上传者</th>
				</tr>
			</thead>
			<tbody>
				{#each files as file}
					<tr>
						<td><a href="/local--files/{pageSlug}/{file.filename}">{file.filename}</a></td>
						<td>{formatSize(file.size || 0)}</td>
						<td>{file.mimetype || ''}</td>
						<td>{file.date_added ? new Date(file.date_added).toLocaleString() : ''}</td>
						<td>{file.user_string || ''}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
{/if}
