import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    stages: [
        { duration: '1m', target: 10 },
    ],
};

const BASE_URL = 'https://abn57op5z4.execute-api.us-east-1.amazonaws.com';
const ENDPOINT = '/prod/text-search';
const INPUT_TEXT = __ENV.INPUT_TEXT || 'red compact suv alloy wheels';
const SIZE = __ENV.SIZE || '1';
const SEARCH_DDB_ONLY = (__ENV.SEARCH_DDB_ONLY || 'alternate').toLowerCase();

function getSearchDdbOnly() {
    if (SEARCH_DDB_ONLY === 'true') {
        return true;
    }

    if (SEARCH_DDB_ONLY === 'false') {
        return false;
    }

    return __ITER % 2 === 0;
}

function buildUrl(searchDdbOnly) {
    const input = encodeURIComponent(INPUT_TEXT);
    return `${BASE_URL}${ENDPOINT}?inputText=${input}&size=${SIZE}&searchDdbOnly=${searchDdbOnly}`;
}

function buildHeaders() {
    const headers = {
        Accept: 'application/json',
    };

    if (__ENV.API_KEY) {
        headers['x-api-key'] = __ENV.API_KEY;
    }

    if (__ENV.BEARER_TOKEN) {
        headers.Authorization = `Bearer ${__ENV.BEARER_TOKEN}`;
    }

    return headers;
}

export default function () {
    const searchDdbOnly = getSearchDdbOnly();
    const url = buildUrl(searchDdbOnly);
    const params = {
        headers: buildHeaders(),
        timeout: '30s',
        tags: {
            variant: searchDdbOnly ? 'ddb_true' : 'ddb_false',
        },
    };

    const res = http.get(url, params);
    check(res, {
        'status is 2xx': (r) => r.status >= 200 && r.status < 300,
    });
    sleep(1);
}
