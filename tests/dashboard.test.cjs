const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function harness() {
    const elements = new Map();
    const element = id => {
        if (!elements.has(id)) elements.set(id, {value: '', textContent: '', checked: false,
            classList: {add() {}, remove() {}}, addEventListener() {}});
        return elements.get(id);
    };
    const context = vm.createContext({document: {addEventListener() {}, getElementById: element,
        querySelectorAll: () => [{value: 'all'}]}, window: {confirm: () => true}, console, setTimeout});
    vm.runInContext(fs.readFileSync('static/js/main.js', 'utf8') + '\nthis.Manager = DashboardManager;', context);
    const manager = new context.Manager();
    manager.showLoading = () => {manager.isLoading = true;};
    manager.hideLoading = () => {manager.isLoading = false;};
    manager.showToast = () => {};
    return {manager, context, element};
}

test('approved caption survives navigation and is the caption sent to Instagram', async () => {
    const {manager, context, element} = harness();
    manager.currentPosts = [{id: 'a', title: 'first'}, {id: 'b', title: 'second'}];
    manager.showPost(0);
    element('caption-editor').value = 'edited first caption';
    let queued;
    manager.addToQueue = post => {queued = post;};
    await manager.handlePostApproval();
    assert.equal(manager.currentIndex, 1);
    assert.equal(queued.caption, 'edited first caption');
    manager.prevPost();
    assert.equal(element('caption-editor').value, 'edited first caption');
    manager.nextPost();
    element('caption-editor').value = 'second caption';
    let sent;
    context.fetch = async (url, options) => {
        sent = JSON.parse(options.body);
        return {ok: true, json: async () => ({status: 'success'})};
    };
    manager.updateQueueItemStatus = () => {};
    await manager.postToInstagram(queued, {querySelector: () => ({disabled: false})});
    assert.equal(sent.caption, 'edited first caption');
});

test('new fetch resets previous index and empty batches stay usable', async () => {
    const {manager, context} = harness();
    manager.currentIndex = 20;
    context.fetch = async () => ({ok: true, json: async () => ({posts: [{id: 'a', title: 'new'}]})});
    await manager.fetchPosts();
    assert.equal(manager.currentIndex, 0);
    context.fetch = async () => ({ok: true, json: async () => ({posts: []})});
    await manager.fetchPosts();
    assert.equal(manager.currentPosts.length, 0);
    assert.equal(manager.isLoading, false);
});

test('backend error text reaches the dashboard toast', async () => {
    const {manager, context} = harness();
    let message;
    manager.showToast = value => {message = value;};
    context.fetch = async () => ({ok: false, status: 400, json: async () => ({message: 'Set Reddit credentials'})});
    await manager.fetchPosts();
    assert.equal(message, 'Set Reddit credentials');
});
