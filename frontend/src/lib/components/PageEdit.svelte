<script lang="ts">
	import { api } from '$lib/api';

	let { title, source, onSave, onCancel } = $props<{
		title: string;
		source: string;
		onSave: (event: CustomEvent<{title: string; source: string; comment: string}>) => void;
		onCancel: () => void;
	}>();

	let editTitle = $state(title);
	let editSource = $state(source);
	let comment = $state('');
	let previewHtml = $state('');
	let showPreview = $state(false);

	function handleSave() {
		onSave(new CustomEvent('save', {
			detail: { title: editTitle, source: editSource, comment }
		}));
	}

	async function handlePreview() {
		if (!showPreview) {
			try {
				const result = await api.ajaxModule('Empty', { source: editSource, render: true });
				previewHtml = result.body || '<p><em>预览不可用。</em></p>';
			} catch {
				previewHtml = '<p><em>预览失败。</em></p>';
			}
		}
		showPreview = !showPreview;
	}

	function insertMarkup(before: string, after: string = '') {
		editSource += before + after;
	}
</script>

<div class="edit-page-form">
	<h2>
		{#if title}
			编辑：{title}
		{:else}
			创建新页面
		{/if}
	</h2>

	<div style="margin: 0.5em 0;">
		<label for="edit-title"><strong>页面标题：</strong></label>
		<input type="text" id="edit-title" bind:value={editTitle}>
	</div>

	<!-- Editor Toolbar -->
	<div class="editor-toolbar" style="margin: 0.3em 0; padding: 0.3em; background: #f0f0f0; border: 1px solid #ccc; font-size: 0.85em;">
		<button type="button" title="Bold" onclick={() => editSource += '**bold**'}>B</button>
		<button type="button" title="Italic" onclick={() => editSource += '//italic//'}>I</button>
		<button type="button" title="Underline" onclick={() => editSource += '__underline__'}>U</button>
		<button type="button" title="Strikethrough" onclick={() => editSource += '--strike--'}>S</button>
		|
		<button type="button" title="Heading" onclick={() => editSource += '\n+ Heading\n'}>H</button>
		<button type="button" title="Link" onclick={() => editSource += '[[[page-name | link text]]]'}>Link</button>
		<button type="button" title="Image" onclick={() => editSource += '[[image filename]]'}>Img</button>
		<button type="button" title="Code" onclick={() => editSource += '[[code]]\ncode here\n[[/code]]'}>Code</button>
	</div>

	<div style="margin: 0.5em 0;">
		<textarea bind:value={editSource} rows="25"></textarea>
	</div>

	<div style="margin: 0.5em 0;">
		<label for="edit-comment"><strong>修改说明：</strong></label>
		<input type="text" id="edit-comment" bind:value={comment} placeholder="可选备注">
	</div>

	<div class="buttons">
		<button onclick={handleSave}>保存</button>
		<button onclick={handlePreview}>{showPreview ? '隐藏预览' : '预览'}</button>
		<button onclick={onCancel}>取消</button>
	</div>

	{#if showPreview && previewHtml}
		<div class="preview-box" style="border: 1px solid #ccc; padding: 1em; margin-top: 1em;">
			<h3>预览</h3>
			{@html previewHtml}
		</div>
	{/if}
</div>
