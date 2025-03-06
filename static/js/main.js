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
        document.getElementById('prev-post').addEventListener('click', () => this.navigatePosts('prev'));
        document.getElementById('next-post').addEventListener('click', () => this.navigatePosts('next'));

        // Approve/Reject buttons
        document.getElementById('approve-post').addEventListener('click', () => this.handlePostApproval());
        document.getElementById('reject-post').addEventListener('click', () => this.handlePostRejection());

        // Add subreddit button
        document.getElementById('add-subreddit').addEventListener('click', () => this.addCustomSubreddit());
    }

    showLoading(message = 'Loading...') {
        const overlay = document.getElementById('loading-overlay');
        const loadingMessage = overlay.querySelector('.loading-message');
        loadingMessage.textContent = message;
        overlay.classList.remove('d-none');
        this.isLoading = true;
    }

    hideLoading() {
        document.getElementById('loading-overlay').classList.add('d-none');
        this.isLoading = false;
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
                ${message}
            </div>
        `;
        toastContainer.appendChild(toast);

        // Remove toast after 5 seconds
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

    async fetchPosts() {
        try {
            this.showLoading('Fetching posts...');

            const selectedSubreddits = Array.from(document.querySelectorAll('input[type="checkbox"]:checked'))
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

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            this.currentPosts = data.posts;
            this.updatePostsCount();
            this.showToast(`Successfully fetched ${data.posts.length} posts`);

        } catch (error) {
            this.showToast(error.message, 'danger');
            console.error('Error fetching posts:', error);
        } finally {
            this.hideLoading();
        }
    }

    async handlePostApproval() {
        try {
            const post = this.currentPosts[this.currentIndex];
            this.showLoading('Processing approval...');

            // Add to approved posts
            this.approvedPosts.push(post);
            this.updatePostsCount();
            this.addToQueue(post);

            this.showToast('Post approved and added to queue');
            this.navigatePosts('next');

        } catch (error) {
            this.showToast('Error approving post', 'danger');
            console.error('Error approving post:', error);
        } finally {
            this.hideLoading();
        }
    }

    async postToInstagram(post, row) {
        try {
            this.showLoading('Posting to Instagram...');

            const response = await fetch('/post-to-instagram', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(post)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.status === 'success') {
                this.updateQueueItemStatus(row, 'success');
                this.showToast('Successfully posted to Instagram');
            } else {
                throw new Error(result.message);
            }

        } catch (error) {
            this.updateQueueItemStatus(row, 'error');
            this.showToast('Failed to post to Instagram', 'danger');
            console.error('Error posting to Instagram:', error);
        } finally {
            this.hideLoading();
        }
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

    updatePostsCount() {
        document.getElementById('posts-fetched-count').textContent = this.currentPosts.length;
        document.getElementById('posts-approved-count').textContent = this.approvedPosts.length;
    }
}


document.addEventListener('DOMContentLoaded', function() {
    window.dashboardManager = new DashboardManager();
});

document.addEventListener('DOMContentLoaded', function () {
    const setupForm = document.getElementById('setupForm');
    if (setupForm) {
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

document.addEventListener('DOMContentLoaded', function() {
    // Initialize variables
    let currentPosts = [];
    let currentIndex = 0;
    let approvedPosts = [];

    // Fetch posts button handler
    document.getElementById('fetch-posts').addEventListener('click', async () => {
    const selectedSubreddits = Array.from(document.querySelectorAll('input[type="checkbox"]:checked'))
    .map(cb => cb.value);

    try {
    const response = await fetch('/fetch-posts', {
    method: 'POST',
    headers: {
    'Content-Type': 'application/json',
},
    body: JSON.stringify({subreddits: selectedSubreddits})
});

    const data = await response.json();
    currentPosts = data.posts;
    document.getElementById('posts-fetched-count').textContent = currentPosts.length;
    showPost(0);
} catch (error) {
    console.error('Error fetching posts:', error);
    alert('Error fetching posts. Please try again.');
}
});

    // Add custom subreddit handler
    document.getElementById('add-subreddit').addEventListener('click', () => {
    const input = document.getElementById('custom-subreddit');
    const subreddit = input.value.trim();

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
});

    // Navigation handlers
    document.getElementById('prev-post').addEventListener('click', () => {
    if (currentIndex > 0) {
    showPost(currentIndex - 1);
}
});

    document.getElementById('next-post').addEventListener('click', () => {
    if (currentIndex < currentPosts.length - 1) {
    showPost(currentIndex + 1);
}
});

    // Approve/Reject handlers
    document.getElementById('approve-post').addEventListener('click', () => {
    const post = currentPosts[currentIndex];
    approvedPosts.push(post);
    document.getElementById('posts-approved-count').textContent = approvedPosts.length;
    addToQueue(post);
    nextPost();
});

    document.getElementById('reject-post').addEventListener('click', () => {
    nextPost();
});

    function showPost(index) {
    if (currentPosts.length === 0) {
    document.getElementById('post-review-container').classList.add('d-none');
    document.getElementById('no-posts-message').classList.remove('d-none');
    return;
}

    const post = currentPosts[index];
    currentIndex = index;

    document.getElementById('post-review-container').classList.remove('d-none');
    document.getElementById('no-posts-message').classList.add('d-none');

    document.getElementById('post-title').textContent = post.title;
    document.getElementById('post-subreddit').textContent = `r/${post.subreddit}`;
    document.getElementById('post-author').textContent = `u/${post.author}`;
    document.getElementById('post-score').textContent = `${post.score} points`;
    document.getElementById('post-media').src = post.url;

    // Update caption preview
    document.getElementById('caption-text').textContent = generateCaption(post);

    // Update navigation buttons
    document.getElementById('prev-post').disabled = index === 0;
    document.getElementById('next-post').disabled = index === currentPosts.length - 1;
}

    function nextPost() {
    if (currentIndex < currentPosts.length - 1) {
    showPost(currentIndex + 1);
} else {
    showPost(currentIndex);
}
}

    function addToQueue(post) {
    const tbody = document.getElementById('queue-table-body');
    const row = document.createElement('tr');
    row.innerHTML = `
            <td>${post.title}</td>
            <td>r/${post.subreddit}</td>
            <td><span class="badge bg-warning">Pending</span></td>
            <td>
                <button class="btn btn-sm btn-primary post-now-btn">Post Now</button>
                <button class="btn btn-sm btn-danger remove-btn">Remove</button>
            </td>
        `;
    tbody.appendChild(row);

    // Add handlers for the new buttons
    row.querySelector('.post-now-btn').addEventListener('click', () => postToInstagram(post, row));
    row.querySelector('.remove-btn').addEventListener('click', () => row.remove());
}

    async function postToInstagram(post, row) {
    try {
    const response = await fetch('/post-to-instagram', {
    method: 'POST',
    headers: {
    'Content-Type': 'application/json',
},
    body: JSON.stringify(post)
});

    const result = await response.json();
    if (result.status === 'success') {
    row.querySelector('td:nth-child(3) span').className = 'badge bg-success';
    row.querySelector('td:nth-child(3) span').textContent = 'Posted';
    row.querySelector('.post-now-btn').disabled = true;

    const postedCount = document.getElementById('posts-posted-count');
    postedCount.textContent = parseInt(postedCount.textContent) + 1;
} else {
    throw new Error(result.message);
}
} catch (error) {
    console.error('Error posting to Instagram:', error);
    alert('Error posting to Instagram. Please try again.');
}
}

    function generateCaption(post) {
    return `${post.title} 🔥🔥🔥\n\n#mma #ufc #viral #fyp #mixedmartialarts #mmafighter #mmanews #ufcnews #mmacommunity #ufcfighter #champion #mmafighters #wrestling #kickboxing #boxing #combatsports #mixedmartialarts #bjj #mmastriking #submission #mmatraining #ko #muaythai #jiujitsu`;
}
});