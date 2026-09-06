import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router';
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';

window.scrollTo = vi.fn();

const navigate = vi.fn();
vi.mock('react-router', async () => ({
  ...(await vi.importActual('react-router')),
  useNavigate: () => navigate,
}));

vi.mock('../services/api', () => ({
  apiFetch: vi.fn(),
  extractApiError: vi.fn(async (res) => (await res.json())?.type?.[0] ?? null),
  getCsrfToken: () => 'tok',
}));

import { apiFetch } from '../services/api';
import AddThingPage from './AddThingPage';

// The form a member meets first in a COMMUNITY collection, and the one place a
// collection's `allowed_thing_types` has to be honoured in the UI: the backend
// refuses a type outside the list with a 400, so a picker that still offers it
// sends people down a path that cannot succeed.

const collection = (over = {}) => ({
  code: 'COL001',
  headline: 'The lending library',
  allowed_thing_types: [],
  tags: [],
  ...over,
});

function mockApi({ coll = collection(), post = { ok: true, body: {} } } = {}) {
  apiFetch.mockImplementation((url, opts) => {
    if (opts?.method === 'POST') {
      return Promise.resolve({
        ok: post.ok,
        status: post.status ?? (post.ok ? 201 : 400),
        json: async () => post.body,
      });
    }
    return Promise.resolve({ ok: true, status: 200, json: async () => coll });
  });
}

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={['/collections/COL001/add']}>
      <Routes>
        <Route path="/collections/:code/add" element={<AddThingPage />} />
      </Routes>
    </MemoryRouter>
  );

const postBody = () => {
  const call = apiFetch.mock.calls.find(([, o]) => o?.method === 'POST');
  return call && JSON.parse(call[1].body);
};

const openTypePicker = async () => {
  fireEvent.click(await screen.findByRole('combobox', { name: /Type/ }));
};

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem('userCode', 'USR001');
  vi.clearAllMocks();
});
afterEach(() => vi.restoreAllMocks());

describe('AddThingPage — the collection decides which types exist', () => {
  test('with no allowlist, every type is on offer', async () => {
    mockApi();
    renderPage();
    await openTypePicker();

    for (const label of ['Gift', 'Sale', 'Rental', 'Lend']) {
      expect(screen.getByRole('option', { name: label })).toBeInTheDocument();
    }
  });

  test('an allowlist hides the types the collection would refuse', async () => {
    // A lending library that accepts only loans must not offer "Gift": the
    // backend answers 400 on it, so offering it is an invitation to fail.
    mockApi({ coll: collection({ allowed_thing_types: ['LEND_THING', 'RENT_THING'] }) });
    renderPage();
    await openTypePicker();

    expect(screen.getByRole('option', { name: 'Lend' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Rental' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Gift' })).toBeNull();
    expect(screen.queryByRole('option', { name: 'Sale' })).toBeNull();
  });

  test('a single allowed type is chosen for the member, not asked of them', async () => {
    // With one possible answer, asking the question is friction — and the
    // downstream fields (dates, fee) only appear once a type is picked.
    mockApi({ coll: collection({ allowed_thing_types: ['SELL_THING'] }) });
    renderPage();

    // The fee field belongs to SELL, so its presence proves the pre-selection
    // reached the form rather than only the select's own value.
    expect(await screen.findByLabelText(/Price/)).toBeInTheDocument();
  });
});

describe('AddThingPage — what the form sends', () => {
  test('a title and a type are enough, and the collection travels with them', async () => {
    mockApi();
    renderPage();
    await openTypePicker();
    fireEvent.click(screen.getByRole('option', { name: 'Gift' }));
    fireEvent.change(screen.getByLabelText(/Title/), { target: { value: 'Blue armchair' } });

    fireEvent.click(screen.getByRole('button', { name: 'Create' }));

    await waitFor(() =>
      expect(postBody()).toMatchObject({
        type: 'GIFT_THING',
        headline: 'Blue armchair',
        collection_code: 'COL001',
      })
    );
    expect(navigate).toHaveBeenCalledWith('/collections/COL001');
  });

  test('a title of only spaces is not a title', async () => {
    mockApi();
    renderPage();
    await openTypePicker();
    fireEvent.click(screen.getByRole('option', { name: 'Gift' }));
    fireEvent.change(screen.getByLabelText(/Title/), { target: { value: '   ' } });

    fireEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(await screen.findByText('Title is required.')).toBeInTheDocument();
    expect(postBody()).toBeUndefined();
  });

  test('a sale without a price is refused before it reaches the server', async () => {
    // The fee is what makes a sale a sale; a 400 round-trip to learn that is a
    // worse answer than the form saying so.
    mockApi();
    renderPage();
    await openTypePicker();
    fireEvent.click(screen.getByRole('option', { name: 'Sale' }));
    fireEvent.change(screen.getByLabelText(/Title/), { target: { value: 'Old bike' } });

    fireEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(await screen.findByText('Price is required for this type.')).toBeInTheDocument();
    expect(postBody()).toBeUndefined();
  });

  test('the endless toggle only ships when it means something', async () => {
    // `is_endless` is a GIFT/SELL concept — a loan comes back by definition, so
    // sending the flag on one would be describing something that cannot happen.
    mockApi();
    renderPage();
    await openTypePicker();
    fireEvent.click(screen.getByRole('option', { name: 'Gift' }));
    fireEvent.change(screen.getByLabelText(/Title/), { target: { value: 'Seed packets' } });
    fireEvent.click(screen.getByRole('button', { name: /Endless|Sin límite/i }));

    fireEvent.click(screen.getByRole('button', { name: 'Create' }));

    await waitFor(() => expect(postBody()?.is_endless).toBe(true));
  });

  test('a refused create shows the backend’s reason and keeps the form', async () => {
    mockApi({
      post: { ok: false, status: 400, body: { type: ['This collection does not accept gifts.'] } },
    });
    renderPage();
    await openTypePicker();
    fireEvent.click(screen.getByRole('option', { name: 'Gift' }));
    fireEvent.change(screen.getByLabelText(/Title/), { target: { value: 'Blue armchair' } });
    navigate.mockClear();

    fireEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(await screen.findByText('This collection does not accept gifts.')).toBeInTheDocument();
    expect(navigate).not.toHaveBeenCalled();
  });

  test('a rate-limited create says "too many", not "error"', async () => {
    // 429 means "try later"; a generic failure message would send the member
    // back to edit a form that was already correct.
    mockApi({ post: { ok: false, status: 429, body: {} } });
    renderPage();
    await openTypePicker();
    fireEvent.click(screen.getByRole('option', { name: 'Gift' }));
    fireEvent.change(screen.getByLabelText(/Title/), { target: { value: 'Blue armchair' } });

    fireEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(await screen.findByText(/[Tt]oo many/)).toBeInTheDocument();
  });
});

describe('AddThingPage — a member contributing to a COMMUNITY collection', () => {
  // A deployment may vet who offers LEND/RENT of their own — but a member
  // invited to a COMMUNITY collection whose (vetted) owner allow-listed LEND
  // may add one there (core/services/creator_policy). The picker has to reflect
  // that, and not warn about a verb that is not actually withheld here.
  const NARROWED = {
    collection_modes: ['PROPRIETARY'],
    thing_types: ['GIFT_THING', 'SELL_THING'],
    request_url: '/request-access/',
  };

  const mockNarrowed = (coll) =>
    apiFetch.mockImplementation((url, opts) => {
      if (opts?.method === 'POST')
        return Promise.resolve({ ok: true, status: 201, json: async () => ({}) });
      if (url.includes('/auth/me/'))
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ capabilities: NARROWED }),
        });
      return Promise.resolve({ ok: true, status: 200, json: async () => coll });
    });

  beforeEach(() => {
    // useCapabilities caches per account at module scope; a fresh code keeps
    // this from inheriting the null capabilities the tests above leave behind.
    localStorage.setItem('userCode', `MEMBER${Math.random()}`);
  });

  test('an allow-listed verb is offered even though the deployment withholds it', async () => {
    mockNarrowed(
      collection({
        mode: 'COMMUNITY',
        is_member: true,
        allowed_thing_types: ['LEND_THING', 'GIFT_THING'],
      })
    );
    renderPage();
    await openTypePicker();

    expect(await screen.findByRole('option', { name: 'Lend' })).toBeInTheDocument();
    // And the "needs approval" notice does not name it — it is not withheld here.
    expect(screen.queryByText(/need approval/i)).toBeNull();
  });

  test('an empty allowlist still holds an un-vetted member to the open half', async () => {
    // The owner made no type choice, so the member keeps GIFT/SELL and the
    // notice explains the rest — exactly as in a proprietary collection.
    mockNarrowed(collection({ mode: 'COMMUNITY', is_member: true, allowed_thing_types: [] }));
    renderPage();
    await openTypePicker();

    expect(screen.getByRole('option', { name: 'Gift' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Lend' })).toBeNull();
    expect(await screen.findByText(/need approval/i)).toBeInTheDocument();
  });
});
