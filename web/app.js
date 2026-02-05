/* ============================================
   每日靈修 - JavaScript Application
   ============================================ */

// ===== Configuration =====
// TODO: 請替換為您的 Supabase 資訊
const SUPABASE_URL = 'https://xrupcmllpwlnstcalcaj.supabase.co';
const SUPABASE_ANON_KEY = 'sb_publishable_Io0aNJ2mqU9la7eG8xpydA_JaxCQ7mo';

// TODO: 請替換為您的 VAPID Public Key
const VAPID_PUBLIC_KEY = 'BPkD_3iECRU09Wlobb3lJhAd7XmBqH-QIxOComSVJ3Y-oinlQlA5PRETXqENksEY-lfUedCpvq1MemBEdFchdGs';

// ===== State =====
let isSubscribed = false;
let swRegistration = null;

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', async () => {
    // Check if running as PWA (from home screen)
    const isPWA = window.matchMedia('(display-mode: standalone)').matches ||
        window.navigator.standalone === true;

    // Check iOS
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);

    // Register Service Worker
    if ('serviceWorker' in navigator) {
        try {
            // Unregister old service workers first
            const registrations = await navigator.serviceWorker.getRegistrations();
            for (const reg of registrations) {
                await reg.update();
            }

            swRegistration = await navigator.serviceWorker.register('sw.js');
            console.log('Service Worker registered');

            // Check subscription status
            await checkSubscription();
        } catch (error) {
            console.error('Service Worker registration failed:', error);
        }
    }

    // Load content
    await loadContent();

    // Load stats
    await loadStats();
});

// ===== Subscription Functions =====
async function checkSubscription() {
    if (!('PushManager' in window)) {
        updateSubscribeButton('unsupported');
        return;
    }

    try {
        const subscription = await swRegistration.pushManager.getSubscription();
        isSubscribed = subscription !== null;
        updateSubscribeButton(isSubscribed ? 'subscribed' : 'default');
    } catch (error) {
        console.error('Error checking subscription:', error);
    }
}

function updateSubscribeButton(state) {
    const btn = document.getElementById('subscribe-btn');
    const btnText = btn.querySelector('.btn-text');
    const btnIcon = btn.querySelector('.btn-icon');

    switch (state) {
        case 'subscribed':
            btnText.textContent = '已訂閱';
            btnIcon.textContent = '✓';
            btn.classList.add('subscribed');
            btn.disabled = false;
            break;
        case 'unsupported':
            btnText.textContent = '不支援';
            btnIcon.textContent = '⚠️';
            btn.disabled = true;
            break;
        case 'loading':
            btnText.textContent = '處理中...';
            btnIcon.textContent = '⏳';
            btn.disabled = true;
            break;
        default:
            btnText.textContent = '訂閱通知';
            btnIcon.textContent = '🔔';
            btn.classList.remove('subscribed');
            btn.disabled = false;
    }
}

async function handleSubscribe() {
    // Check iOS standalone mode
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    const isPWA = window.matchMedia('(display-mode: standalone)').matches ||
        window.navigator.standalone === true;

    // If iOS and not running as PWA, show instructions
    if (isIOS && !isPWA) {
        showIOSPrompt();
        return;
    }

    if (isSubscribed) {
        await unsubscribe();
    } else {
        await subscribe();
    }
}

async function subscribe() {
    if (!('PushManager' in window)) {
        alert('您的瀏覽器不支援推播通知');
        return;
    }

    updateSubscribeButton('loading');

    try {
        // Request notification permission
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            alert('需要通知權限才能訂閱');
            updateSubscribeButton('default');
            return;
        }

        // Wait for Service Worker to be ready (active)
        const registration = await navigator.serviceWorker.ready;

        // Subscribe to push
        const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
        });

        // Save subscription to Supabase
        const response = await fetch(`${SUPABASE_URL}/rest/v1/push_subscribers`, {
            method: 'POST',
            headers: {
                'apikey': SUPABASE_ANON_KEY,
                'Content-Type': 'application/json',
                'Prefer': 'return=minimal'
            },
            body: JSON.stringify({
                subscription: subscription.toJSON()
            })
        });

        if (response.ok) {
            isSubscribed = true;
            updateSubscribeButton('subscribed');
            alert('訂閱成功！您將於每天早上收到靈修推播');
        } else {
            throw new Error('Failed to save subscription');
        }
    } catch (error) {
        console.error('Subscription error:', error);
        alert('訂閱失敗，請稍後再試');
        updateSubscribeButton('default');
    }
}

async function unsubscribe() {
    updateSubscribeButton('loading');

    try {
        const subscription = await swRegistration.pushManager.getSubscription();
        if (subscription) {
            await subscription.unsubscribe();
        }
        isSubscribed = false;
        updateSubscribeButton('default');
    } catch (error) {
        console.error('Unsubscribe error:', error);
        updateSubscribeButton('subscribed');
    }
}

// ===== Content Functions =====
async function loadContent() {
    const contentList = document.getElementById('content-list');

    try {
        const response = await fetch(
            `${SUPABASE_URL}/rest/v1/daily_bible?order=date.desc&limit=14`,
            {
                headers: {
                    'apikey': SUPABASE_ANON_KEY
                }
            }
        );

        if (!response.ok) {
            throw new Error('Failed to load content');
        }

        const data = await response.json();

        if (data.length === 0) {
            contentList.innerHTML = `
                <div class="loading">
                    <p>尚無內容，請稍後再來 🙏</p>
                </div>
            `;
            return;
        }

        contentList.innerHTML = data.map(item => createContentCard(item)).join('');

        // Increment view count for first item (latest)
        if (data[0]) {
            incrementView(data[0].id);
        }
    } catch (error) {
        console.error('Error loading content:', error);
        contentList.innerHTML = `
            <div class="loading">
                <p>載入失敗，請重新整理頁面</p>
            </div>
        `;
    }
}

function createContentCard(item) {
    const date = new Date(item.date);
    const formattedDate = date.toLocaleDateString('zh-TW', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    const audioHtml = item.audio_url ? `
        <div class="audio-player">
            <audio controls preload="none" onplay="handleAudioPlay('${item.id}')">
                <source src="${item.audio_url}" type="audio/mpeg">
                您的瀏覽器不支援音訊播放
            </audio>
        </div>
    ` : '';

    return `
        <article class="content-card" data-id="${item.id}">
            <div class="card-header">
                <span class="card-date">${formattedDate}</span>
                <div class="card-stats">
                    <span>👁️ ${formatNumber(item.view_count)}</span>
                    <span>🎧 ${formatNumber(item.play_count)}</span>
                </div>
            </div>
            <div class="card-reference">${item.verse_reference}</div>
            <div class="card-verse">${item.verse_text.replace(/\n/g, '<br>')}</div>
            <div class="card-exposition" id="exposition-${item.id}">${item.exposition.replace(/\n/g, '<br>')}</div>
            <div class="card-actions">
                <button class="expand-btn" onclick="toggleExpand('${item.id}')">展開全文</button>
            </div>
            ${audioHtml}
        </article>
    `;
}

function toggleExpand(id) {
    const exposition = document.getElementById(`exposition-${id}`);
    const btn = exposition.parentElement.querySelector('.expand-btn');

    if (exposition.classList.contains('expanded')) {
        exposition.classList.remove('expanded');
        btn.textContent = '展開全文';
    } else {
        exposition.classList.add('expanded');
        btn.textContent = '收合';
    }
}

// ===== Stats Functions =====
async function loadStats() {
    try {
        const response = await fetch(
            `${SUPABASE_URL}/rest/v1/daily_bible?select=view_count,play_count`,
            {
                headers: {
                    'apikey': SUPABASE_ANON_KEY
                }
            }
        );

        if (!response.ok) return;

        const data = await response.json();

        const totalViews = data.reduce((sum, item) => sum + (item.view_count || 0), 0);
        const totalPlays = data.reduce((sum, item) => sum + (item.play_count || 0), 0);

        document.getElementById('total-views').textContent = formatNumber(totalViews);
        document.getElementById('total-plays').textContent = formatNumber(totalPlays);

        // Get subscriber count
        const subResponse = await fetch(
            `${SUPABASE_URL}/rest/v1/push_subscribers?select=id`,
            {
                headers: {
                    'apikey': SUPABASE_ANON_KEY
                }
            }
        );

        if (subResponse.ok) {
            const subs = await subResponse.json();
            document.getElementById('total-subscribers').textContent = formatNumber(subs.length);
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function incrementView(id) {
    try {
        await fetch(`${SUPABASE_URL}/rest/v1/rpc/increment_view`, {
            method: 'POST',
            headers: {
                'apikey': SUPABASE_ANON_KEY,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ row_id: id })
        });
    } catch (error) {
        console.error('Error incrementing view:', error);
    }
}

async function handleAudioPlay(id) {
    try {
        await fetch(`${SUPABASE_URL}/rest/v1/rpc/increment_play`, {
            method: 'POST',
            headers: {
                'apikey': SUPABASE_ANON_KEY,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ row_id: id })
        });
    } catch (error) {
        console.error('Error incrementing play:', error);
    }
}

// ===== UI Functions =====
function showIOSPrompt() {
    document.getElementById('ios-prompt').classList.remove('hidden');
}

function closeIOSPrompt() {
    document.getElementById('ios-prompt').classList.add('hidden');
}

function showAlternativeSubscribe() {
    document.getElementById('alt-subscribe-modal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('alt-subscribe-modal').classList.add('hidden');
}

function showNotification(title, message) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, { body: message });
    }
}

// ===== Utility Functions =====
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}
