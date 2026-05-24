<script lang="ts">
	import '../app.css';
	import { api } from '$lib/api';
	import { onMount } from 'svelte';

	let { children } = $props();

	let user = $state<any>(null);
	let site = $state<any>(null);

	onMount(async () => {
		try {
			user = await api.getProfile();
		} catch { /* not logged in */ }

		const hostname = window.location.hostname;
		const parts = hostname.split('.');
		if (parts.length > 2 && parts[0] !== 'www') {
			const siteSlug = parts[0];
			try {
				site = await api.getSite(siteSlug);
			} catch { /* site not found */ }
		}
	});
</script>

<div id="container">
	{@render children()}
</div>
