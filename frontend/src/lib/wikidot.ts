/**
 * Wikidot-compatible client-side interactivity.
 * Handles collapsible blocks, tabviews, and rating widget behavior.
 */

export function initWikidotInteractivity(container: HTMLElement) {
	initCollapsibles(container);
	initTabviews(container);
}

function initCollapsibles(container: HTMLElement) {
	const blocks = container.querySelectorAll('.collapsible-block');
	blocks.forEach(block => {
		const folded = block.querySelector('.collapsible-block-folded') as HTMLElement;
		const unfolded = block.querySelector('.collapsible-block-unfolded') as HTMLElement;
		if (!folded || !unfolded) return;

		const showLink = folded.querySelector('.collapsible-block-link');
		const hideLink = unfolded.querySelector('.collapsible-block-link');

		showLink?.addEventListener('click', (e) => {
			e.preventDefault();
			folded.style.display = 'none';
			unfolded.style.display = 'block';
		});

		hideLink?.addEventListener('click', (e) => {
			e.preventDefault();
			folded.style.display = 'block';
			unfolded.style.display = 'none';
		});
	});
}

function initTabviews(container: HTMLElement) {
	const tabviews = container.querySelectorAll('.yui-navset');
	tabviews.forEach(tabview => {
		const headers = tabview.querySelectorAll('.tab-header');
		const contents = tabview.querySelectorAll('.tab-content');

		headers.forEach(header => {
			header.addEventListener('click', () => {
				const tabIdx = header.getAttribute('data-tab');

				headers.forEach(h => h.classList.remove('active'));
				contents.forEach(c => {
					(c as HTMLElement).style.display = 'none';
					c.classList.remove('active');
				});

				header.classList.add('active');
				const target = contents[parseInt(tabIdx || '0')] as HTMLElement;
				if (target) {
					target.style.display = 'block';
					target.classList.add('active');
				}
			});
		});
	});
}
