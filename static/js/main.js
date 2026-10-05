document.addEventListener('DOMContentLoaded', function () {
    const pathname = window.location.pathname.replace(/\/+$/, '') || '/';

    if (pathname === '/dashboard') {
        window.dashboardManager = new DashboardManager();
    }

    const setupForm = document.getElementById('setupForm');
    const forgetButton = document.getElementById('forget-credentials');
    if (forgetButton) forgetButton.addEventListener('click', async () => {
        try {
            const response = await fetch('/forget-credentials', {
                method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'
            });
            if (!response.ok) throw new Error('Could not clear credentials');
            window.location.reload();
        } catch (error) {
            alert(error.message);
        }
    });
    if (setupForm) {
        fetch('/configuration-status').then(response => response.json()).then(status => {
            document.getElementById('configuration-status').textContent =
                `Configured: Reddit ${status.reddit_credentials ? 'yes' : 'no'}, Instagram ${status.instagram ? 'yes' : 'no'}, AI ${status.openai ? 'yes' : 'no'}. Blank fields keep saved values.`;
        }).catch(() => {});
        setupForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(setupForm);
            const data = Object.fromEntries(formData.entries());

            try {
                const response = await fetch('/setup', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();
                if (result.status === 'success') {
                    window.location.href = '/dashboard';
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Error: ' + error);
            }
        });
    }
});

class DashboardManager {
    constructor() {
        this.currentPosts = [];
        this.currentIndex = 0;
        this.approvedPosts = [];
        this.isLoading = false;

        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Fetch posts button
        document.getElementById('fetch-posts').addEventListener('click', () => this.fetchPosts());

        // Navigation buttons
        document.getElementById('prev-post').addEventListener('click', () => this.prevPost('prev'));
        document.getElementById('next-post').addEventListener('click', () => this.nextPost('next'));

        // Approve/Reject buttons
        document.getElementById('approve-post').addEventListener('click', () => this.handlePostApproval());
        document.getElementById('reject-post').addEventListener('click', () => this.handlePostRejection());

        // Add subreddit button
        document.getElementById('add-subreddit').addEventListener('click', () => this.addCustomSubreddit());

        document.getElementById('caption-editor').addEventListener('input', () => {
            this.saveCaption();
            this.updateCharCount();
        });
        document.getElementById('reset-caption').addEventListener('click', () => this.resetCaption());
        
        // AI Content Optimization
        document.getElementById('optimize-button').addEventListener('click', () => this.optimizeContent());
        document.getElementById('ai-enabled').addEventListener('change', (e) => {
            document.getElementById('optimize-button').disabled = !e.target.checked;
        });
        document.getElementById('analyze-content').addEventListener('change', (e) => {
            if (e.target.checked) {
                document.getElementById('content-analysis').classList.remove('d-none');
            } else {
                document.getElementById('content-analysis').classList.add('d-none');
            }
        });
    }

    showLoading(message = 'Loading...') {
        const overlay = document.getElementById('loading-overlay');
        const loadingMessage = overlay.querySelector('.loading-message');
        loadingMessage.textContent = message;
        overlay.classList.remove('d-none');
        this.isLoading = true;
    }

    showPost(index) {
        if (this.currentPosts.length === 0) {
            document.getElementById('post-review-container').classList.add('d-none');
            document.getElementById('no-posts-message').classList.remove('d-none');
            return;
        }

        index = Math.max(0, Math.min(index, this.currentPosts.length - 1));
        const post = this.currentPosts[index];
        this.currentIndex = index;

        document.getElementById('post-review-container').classList.remove('d-none');
        document.getElementById('no-posts-message').classList.add('d-none');

        document.getElementById('post-title').textContent = post.title;
        document.getElementById('post-subreddit').textContent = `r/${post.subreddit}`;
        document.getElementById('post-author').textContent = `u/${post.author}`;
        document.getElementById('post-score').textContent = `${post.score} points`;
        document.getElementById('post-media').src = post.url;

        document.getElementById('caption-editor').value = post.caption ?? this.generateDefaultCaption(post);
        this.updateCharCount();
        document.getElementById('content-analysis').classList.add('d-none');

        // Update navigation buttons
        document.getElementById('prev-post').disabled = index === 0;
        document.getElementById('next-post').disabled = index === this.currentPosts.length - 1;
    }

    addCustomSubreddit() {
        const input = document.getElementById('custom-subreddit');
        const subreddit = input.value.trim().replace(/^r\//i, '');
        if (!/^[A-Za-z0-9_]{1,21}$/.test(subreddit)) {
            this.showToast('Enter a valid subreddit name', 'danger');
            return;
        }
        if (Array.from(document.querySelectorAll('#default-subreddits input')).some(cb => cb.value.toLowerCase() === subreddit.toLowerCase())) return;

        if (subreddit) {
            const defaultSubreddits = document.getElementById('default-subreddits');
            const div = document.createElement('div');
            div.className = 'form-check';
            div.innerHTML = `
                <input class="form-check-input" type="checkbox" value="${subreddit}" id="${subreddit}" checked>
                <label class="form-check-label" for="${subreddit}">r/${subreddit}</label>
            `;
            defaultSubreddits.appendChild(div);
            input.value = '';
        }
    }

    hideLoading() {
        document.getElementById('loading-overlay').classList.add('d-none');
        this.isLoading = false;
    }

    nextPost() {
        if (this.isLoading) return;
        if (this.currentIndex < this.currentPosts.length - 1) {
            this.showPost(this.currentIndex + 1);
        } else {
            this.showPost(this.currentIndex);
        }
    }

    prevPost() {
        if (this.isLoading) return;
        if (this.currentIndex > 0) {
            this.showPost(this.currentIndex - 1);
        } else {
            this.showPost(this.currentIndex);
        }
    }

    showToast(message, type = 'success') {
        const toastContainer = document.querySelector('.toast-container');
        const toast = document.createElement('div');
        toast.className = `toast show bg-${type} text-white`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="toast-header">
                <strong class="me-auto">${type === 'success' ? 'Success' : 'Error'}</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">

            </div>
        `;
        toast.querySelector('.toast-body').textContent = message;
        toastContainer.appendChild(toast);

        // Remove toast after 5 seconds
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

    async fetchPosts() {
        if (this.isLoading) return;
        try {
            this.showLoading('Fetching posts...');

            const selectedSubreddits = Array.from(document.querySelectorAll('#default-subreddits input[type="checkbox"]:checked'))
                .map(cb => cb.value);

            if (selectedSubreddits.length === 0) {
                throw new Error('Please select at least one subreddit');
            }

            const response = await fetch('/fetch-posts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({subreddits: selectedSubreddits})
            });

            const data = await response.json();
            if (!response.ok || data.error) {
                throw new Error(data.message || data.error || `HTTP ${response.status}`);
            }

            this.currentPosts = data.posts;
            this.currentIndex = 0;
            this.updatePostsCount();
            this.showToast(`Successfully fetched ${data.posts.length} posts`);
            this.showPost(this.currentIndex);
            (data.warnings || []).forEach(message => this.showToast(message, 'warning'));

        } catch (error) {
            this.showToast(error.message, 'danger');
            console.error('Error fetching posts:', error);
        } finally {
            this.hideLoading();
        }
    }

    addToQueue(post) {
        const tbody = document.getElementById('queue-table-body');
        const row = document.createElement('tr');
        row.innerHTML = `
            <td></td>
            <td></td>
            <td><span class="badge bg-warning">Pending</span></td>
            <td>
                <button class="btn btn-sm btn-primary post-now-btn">Post Now</button>
                <button class="btn btn-sm btn-danger remove-btn">Remove</button>
            </td>
        `;
        row.children[0].textContent = post.title;
        row.children[1].textContent = `r/${post.subreddit}`;
        tbody.appendChild(row);

        // Add handlers for the new buttons
        row.querySelector('.post-now-btn').addEventListener('click', () => this.postToInstagram(post, row));
        row.querySelector('.remove-btn').addEventListener('click', () => {
            this.approvedPosts = this.approvedPosts.filter(item => item !== post);
            row.remove();
            this.updatePostsCount();
        });
    }

    async postToInstagram(post, row) {
        if (this.isLoading || row.querySelector('.post-now-btn').disabled) return;
        if (!window.confirm('Publish this queued post to Instagram now?')) return;
        try {
            this.showLoading('Posting to Instagram...');

            // Get the edited caption
            const caption = post.caption;

            const postData = {
                ...post,
                caption: caption // Include the edited caption
            };

            const response = await fetch('/post-to-instagram', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(postData)
            });

            const result = await response.json();
            if (response.ok && result.status === 'success') {
                this.updateQueueItemStatus(row, 'success');
                this.showToast('Successfully posted to Instagram');
            } else {
                throw new Error(result.message);
            }

        } catch (error) {
            this.updateQueueItemStatus(row, 'error');
            this.showToast(error.message || 'Failed to post to Instagram', 'danger');
            console.error('Error posting to Instagram:', error);
        } finally {
            this.hideLoading();
        }
    }

    async handlePostApproval() {
        if (this.isLoading || !this.currentPosts.length) return;
        try {
            this.saveCaption();
            const post = {...this.currentPosts[this.currentIndex]};
            if (this.approvedPosts.some(item => item.id === post.id)) {
                this.showToast('This post is already in the queue', 'warning');
                return;
            }
            this.showLoading('Processing approval...');

            // Add to approved posts
            this.approvedPosts.push(post);
            this.updatePostsCount();
            this.addToQueue(post);
            
            this.showToast('Post approved and added to queue');
            this.showPost(Math.min(this.currentIndex + 1, this.currentPosts.length - 1));

        } catch (error) {
            this.showToast('Error approving post', 'danger');
            console.error('Error approving post:', error);
        } finally {
            this.hideLoading();
        }
    }

    async handlePostRejection() {
        if (this.isLoading) return;
        this.nextPost();
    }

    updateQueueItemStatus(row, status) {
        const statusBadge = row.querySelector('td:nth-child(3) span');
        const postButton = row.querySelector('.post-now-btn');

        if (status === 'success') {
            statusBadge.className = 'badge bg-success';
            statusBadge.textContent = 'Posted';
            postButton.disabled = true;

            const postedCount = document.getElementById('posts-posted-count');
            postedCount.textContent = parseInt(postedCount.textContent) + 1;
        } else {
            statusBadge.className = 'badge bg-danger';
            statusBadge.textContent = 'Failed';
        }
    }

    generateDefaultCaption(post) {
        return `${post.title} 🔥🔥🔥 #viral #fyp`;
    }

    updatePostsCount() {
        document.getElementById('posts-fetched-count').textContent = this.currentPosts.length;
        document.getElementById('posts-approved-count').textContent = this.approvedPosts.length;
    }

    updateCharCount() {
        const caption = document.getElementById('caption-editor').value;
        document.getElementById('caption-char-count').textContent = caption.length;
    }

    saveCaption() {
        const post = this.currentPosts[this.currentIndex];
        if (post) post.caption = document.getElementById('caption-editor').value;
    }

    resetCaption() {
        const post = this.currentPosts[this.currentIndex];
        if (!post || this.isLoading) return;
        document.getElementById('caption-editor').value = this.generateDefaultCaption(post);
        this.saveCaption();
        this.updateCharCount();
    }

    async optimizeContent() {
        try {
            if (!this.currentPosts.length || this.isLoading) return;
            
            const post = this.currentPosts[this.currentIndex];
            const caption = document.getElementById('caption-editor').value;
            
            this.showLoading('Optimizing content with AI...');
            
            const optimizationLevel = document.getElementById('optimization-level').value;
            const generateHashtags = document.getElementById('generate-hashtags').checked;
            const analyzeContent = document.getElementById('analyze-content').checked;
            
            const response = await fetch('/optimize-content', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: post.title,
                    caption: caption,
                    subreddit: post.subreddit,
                    optimization_level: optimizationLevel,
                    generate_hashtags: generateHashtags,
                    analyze_content: analyzeContent
                })
            });
            
            const result = await response.json();
            if (!response.ok || result.status === 'error') {
                throw new Error(result.message);
            }
            
            // Update caption with optimized version
            document.getElementById('caption-editor').value = result.optimized_caption;
            this.saveCaption();
            this.updateCharCount();
            
            // If analysis is available, update the analysis section
            if (result.analysis) {
                this.updateContentAnalysis(result.analysis);
            }
            
            this.showToast('Content successfully optimized by AI');
            
        } catch (error) {
            this.showToast(error.message, 'danger');
            console.error('Error optimizing content:', error);
        } finally {
            this.hideLoading();
        }
    }
    
    updateContentAnalysis(analysis) {
        const contentAnalysis = document.getElementById('content-analysis');
        contentAnalysis.classList.remove('d-none');
        
        // Update sentiment
        const sentimentValue = document.getElementById('sentiment-value');
        sentimentValue.textContent = analysis.sentiment.charAt(0).toUpperCase() + analysis.sentiment.slice(1);
        
        // Set appropriate badge color
        sentimentValue.className = 'badge';
        if (analysis.sentiment === 'positive') {
            sentimentValue.classList.add('bg-success');
        } else if (analysis.sentiment === 'negative') {
            sentimentValue.classList.add('bg-danger');
        } else {
            sentimentValue.classList.add('bg-primary');
        }
        
        // Update engagement prediction
        const engagementValue = document.getElementById('engagement-value');
        engagementValue.textContent = analysis.engagement_prediction.charAt(0).toUpperCase() + analysis.engagement_prediction.slice(1);
        
        // Set appropriate badge color
        engagementValue.className = 'badge';
        if (analysis.engagement_prediction === 'high') {
            engagementValue.classList.add('bg-success');
        } else if (analysis.engagement_prediction === 'low') {
            engagementValue.classList.add('bg-danger');
        } else {
            engagementValue.classList.add('bg-warning');
            engagementValue.classList.add('text-dark');
        }
        
        // Update topics
        const topicsContainer = document.getElementById('topics-container');
        topicsContainer.innerHTML = '';
        
        analysis.topics.forEach(topic => {
            const badge = document.createElement('span');
            badge.className = 'badge bg-secondary me-1 mb-1';
            badge.textContent = topic;
            topicsContainer.appendChild(badge);
        });
    }
}
