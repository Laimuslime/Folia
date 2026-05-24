<script lang="ts">
	import { api } from '$lib/api';

	interface Plan {
		id: number;
		name: string;
		display_name: string;
		price_monthly: number;
		price_yearly: number;
		max_pages: number;
		max_storage: number;
		max_upload_size: number;
		max_members: number;
		allow_custom_domain: boolean;
		allow_private: boolean;
		remove_branding: boolean;
	}

	interface Subscription {
		plan: Plan | null;
		status: string;
		period: string | null;
		current_period_end: string | null;
	}

	let plans: Plan[] = $state([]);
	let subscription: Subscription | null = $state(null);
	let loading = $state(true);
	let period: 'monthly' | 'yearly' = $state('monthly');
	let showPayModal = $state(false);
	let paymentQrUrl = $state('');
	let paymentOrderId = $state(0);
	let payChannel: 'wechat' | 'alipay' = $state('wechat');
	let polling = $state(false);
	let paySuccess = $state(false);

	async function loadData() {
		try {
			const [p, s] = await Promise.all([api.getPlans(), api.getSubscription()]);
			plans = p;
			subscription = s;
		} catch (e) {
			console.error(e);
		} finally {
			loading = false;
		}
	}

	loadData();

	function formatStorage(bytes: number): string {
		if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(0)}GB`;
		return `${(bytes / 1048576).toFixed(0)}MB`;
	}

	function formatPrice(cents: number): string {
		return `¥${(cents / 100).toFixed(0)}`;
	}

	async function handleUpgrade(plan: Plan) {
		showPayModal = true;
		paySuccess = false;
		paymentQrUrl = '';

		try {
			const result = await api.createOrder(plan.id, period, payChannel);
			paymentQrUrl = result.qr_url || result.pay_url;
			paymentOrderId = result.order_id;
			startPolling();
		} catch (e: any) {
			alert(e.message || '创建订单失败');
			showPayModal = false;
		}
	}

	let pollTimer: ReturnType<typeof setInterval> | null = null;

	function startPolling() {
		polling = true;
		pollTimer = setInterval(async () => {
			try {
				const status = await api.getOrderStatus(paymentOrderId);
				if (status.status === 'paid') {
					polling = false;
					paySuccess = true;
					if (pollTimer) clearInterval(pollTimer);
					setTimeout(() => location.reload(), 2000);
				}
			} catch {}
		}, 3000);
	}

	function closeModal() {
		showPayModal = false;
		if (pollTimer) clearInterval(pollTimer);
		polling = false;
	}
</script>

{#if loading}
	<div class="billing-loading">加载中...</div>
{:else}
	<div class="billing-page">
		<h2>套餐与订阅</h2>

		{#if subscription?.plan}
			<div class="current-plan">
				<span>当前套餐：<strong>{subscription.plan.display_name}</strong></span>
				{#if subscription.current_period_end}
					<span class="period-end">到期时间：{new Date(subscription.current_period_end).toLocaleDateString('zh-CN')}</span>
				{/if}
			</div>
		{/if}

		<div class="period-toggle">
			<button class:active={period === 'monthly'} onclick={() => period = 'monthly'}>月付</button>
			<button class:active={period === 'yearly'} onclick={() => period = 'yearly'}>年付 <span class="save-badge">省17%</span></button>
		</div>

		<div class="plans-grid">
			{#each plans as plan}
				<div class="plan-card" class:current={subscription?.plan?.name === plan.name}>
					<h3>{plan.display_name}</h3>
					<div class="price">
						{#if plan.price_monthly === 0}
							<span class="amount">免费</span>
						{:else}
							<span class="amount">{formatPrice(period === 'yearly' ? plan.price_yearly : plan.price_monthly)}</span>
							<span class="unit">/{period === 'yearly' ? '年' : '月'}</span>
						{/if}
					</div>
					<ul class="features">
						<li>{plan.max_pages > 0 ? `${plan.max_pages} 页面` : '无限页面'}</li>
						<li>{formatStorage(plan.max_storage)} 存储</li>
						<li>{formatStorage(plan.max_upload_size)} 单文件上传</li>
						<li>{plan.max_members > 0 ? `${plan.max_members} 成员` : '无限成员'}</li>
						<li class:disabled={!plan.allow_custom_domain}>自定义域名</li>
						<li class:disabled={!plan.allow_private}>私有站点</li>
						<li class:disabled={!plan.remove_branding}>去除水印</li>
					</ul>
					{#if subscription?.plan?.name === plan.name}
						<button class="btn-current" disabled>当前套餐</button>
					{:else if plan.price_monthly > 0}
						<button class="btn-upgrade" onclick={() => handleUpgrade(plan)}>升级</button>
					{/if}
				</div>
			{/each}
		</div>
	</div>
{/if}

<!-- PAYMENT_MODAL_PLACEHOLDER -->

{#if showPayModal}
	<div class="modal-overlay" onclick={closeModal} role="dialog" aria-modal="true">
		<div class="modal-content" onclick={(e) => e.stopPropagation()} role="document">
			{#if paySuccess}
				<div class="pay-success">
					<div class="success-icon">✓</div>
					<p>支付成功！页面即将刷新...</p>
				</div>
			{:else}
				<h3>扫码支付</h3>
				<div class="channel-select">
					<button class:active={payChannel === 'wechat'} onclick={() => payChannel = 'wechat'}>微信支付</button>
					<button class:active={payChannel === 'alipay'} onclick={() => payChannel = 'alipay'}>支付宝</button>
				</div>
				{#if paymentQrUrl}
					<div class="qr-container">
						<img src={paymentQrUrl} alt="支付二维码" />
					</div>
					<p class="scan-hint">请使用{payChannel === 'wechat' ? '微信' : '支付宝'}扫码支付</p>
				{:else}
					<p>正在生成支付码...</p>
				{/if}
				<button class="btn-cancel" onclick={closeModal}>取消</button>
			{/if}
		</div>
	</div>
{/if}

<style>
	.billing-page { max-width: 900px; margin: 0 auto; padding: 2rem 1rem; }
	.billing-loading { text-align: center; padding: 3rem; color: #666; }
	h2 { text-align: center; margin-bottom: 1.5rem; }
	.current-plan { text-align: center; margin-bottom: 1.5rem; padding: 0.75rem; background: #f0f9ff; border-radius: 8px; display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; }
	.period-end { color: #666; }
	.period-toggle { display: flex; justify-content: center; gap: 0.5rem; margin-bottom: 2rem; }
	.period-toggle button { padding: 0.5rem 1.5rem; border: 1px solid #ddd; border-radius: 6px; background: #fff; cursor: pointer; }
	.period-toggle button.active { background: #2563eb; color: #fff; border-color: #2563eb; }
	.save-badge { font-size: 0.75rem; background: #dcfce7; color: #166534; padding: 0.1rem 0.4rem; border-radius: 4px; }
	.plans-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; }
	.plan-card { border: 2px solid #e5e7eb; border-radius: 12px; padding: 2rem; text-align: center; }
	.plan-card.current { border-color: #2563eb; }
	.plan-card h3 { margin: 0 0 1rem; }
	.price { margin-bottom: 1.5rem; }
	.price .amount { font-size: 2rem; font-weight: 700; }
	.price .unit { color: #666; }
	.features { list-style: none; padding: 0; margin: 0 0 1.5rem; text-align: left; }
	.features li { padding: 0.4rem 0; padding-left: 1.5rem; position: relative; }
	.features li::before { content: '✓'; position: absolute; left: 0; color: #16a34a; }
	.features li.disabled { color: #9ca3af; }
	.features li.disabled::before { content: '—'; color: #9ca3af; }
	.btn-upgrade { width: 100%; padding: 0.75rem; background: #2563eb; color: #fff; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
	.btn-upgrade:hover { background: #1d4ed8; }
	.btn-current { width: 100%; padding: 0.75rem; background: #f3f4f6; color: #6b7280; border: none; border-radius: 8px; font-size: 1rem; }
	.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
	.modal-content { background: #fff; border-radius: 12px; padding: 2rem; min-width: 320px; text-align: center; }
	.channel-select { display: flex; gap: 0.5rem; justify-content: center; margin: 1rem 0; }
	.channel-select button { padding: 0.4rem 1rem; border: 1px solid #ddd; border-radius: 6px; background: #fff; cursor: pointer; }
	.channel-select button.active { background: #2563eb; color: #fff; border-color: #2563eb; }
	.qr-container { margin: 1rem auto; }
	.qr-container img { max-width: 200px; border-radius: 8px; }
	.scan-hint { color: #666; font-size: 0.9rem; }
	.btn-cancel { margin-top: 1rem; padding: 0.5rem 2rem; border: 1px solid #ddd; border-radius: 6px; background: #fff; cursor: pointer; }
	.pay-success { padding: 2rem; }
	.success-icon { font-size: 3rem; color: #16a34a; margin-bottom: 1rem; }
</style>

