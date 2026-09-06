import { useEffect, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router';
import { useTranslation } from 'react-i18next';
import { Button, Notification } from 'hds-react';
import { TYPE_VALUES, FEE_TYPES, DATE_TYPES, DETAIL_TYPES } from '../constants/things';
import { apiFetch, extractApiError } from '../services/api';
import PageLayout from '../components/PageLayout';
import ThingForm from '../components/ThingForm';
import BulkAddCsv from '../components/BulkAddCsv';
import Toast from '../components/Toast';
import useTheeeme from '../hooks/useTheeeme';
import useCapabilities, { isOfferable } from '../hooks/useCapabilities';
import { useLocalized, localizedCounter } from '../utils/localized';

export default function AddThingPage() {
  const { t } = useTranslation();
  // Owner content (headlines, tags) may carry one text per language.
  const L = useLocalized();
  const { code } = useParams();
  const navigate = useNavigate();
  const routerLocation = useLocation();

  const userCode = localStorage.getItem('userCode');
  useEffect(() => {
    document.title = t('titles.addThing');
  }, [t]);

  // Deep-link from the collection empty state: /add#bulk-add scrolls to the CSV importer.
  useEffect(() => {
    if (routerLocation.hash === '#bulk-add') {
      document.getElementById('bulk-add')?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [routerLocation.hash]);

  const [collectionHeadline, setCollectionHeadline] = useState('');
  const [type, setType] = useState('GIFT_THING');
  const [headline, setHeadline] = useState('');
  const [description, setDescription] = useState('');
  const [thumbnail, setThumbnail] = useState('');
  const [fee, setFee] = useState('');
  const [deposit, setDeposit] = useState('');
  const [availability, setAvailability] = useState('');
  const [location, setLocation] = useState('');
  const [condition, setCondition] = useState('');
  const [isEndless, setIsEndless] = useState(false);
  const [gallery, setGallery] = useState([]);
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState(null);

  const capabilities = useCapabilities();
  const [collectionAllowedTypes, setCollectionAllowedTypes] = useState([]);
  const [collectionTags, setCollectionTags] = useState([]);
  // A member contributing to a COMMUNITY collection they were invited to may
  // offer any type its (vetted) owner allow-listed, whatever this deployment's
  // creator policy says about them personally — the same exception the backend
  // applies in `community_contribution_types` (core/services/creator_policy).
  const [contributingToCommunity, setContributingToCommunity] = useState(false);
  const [tags, setTags] = useState([]);

  useEffect(() => {
    if (!userCode) return;
    apiFetch(`/api/v1/collections/${code}/`)
      .then((res) => (res.ok ? res.json() : {}))
      .then((data) => {
        setCollectionHeadline(data.headline || '');
        const allowed = data.allowed_thing_types || [];
        setCollectionAllowedTypes(allowed);
        setContributingToCommunity(data.mode === 'COMMUNITY' && !!data.is_member);
        setCollectionTags(data.tags || []);
        // If the allowlist names a single type, pre-select it so the form
        // immediately shows the right downstream fields.
        if (allowed.length === 1) {
          setType(allowed[0]);
        }
      })
      .catch(() => {});
  }, [userCode, code]);

  const computeErrors = () => {
    const newErrors = {};
    if (!headline.trim()) newErrors.headline = t('addThing.titleRequired');
    else if (localizedCounter(headline, 64).over) newErrors.headline = t('addThing.maxHeadline');
    if (localizedCounter(description, 256).over)
      newErrors.description = t('addThing.maxDescription');
    if (FEE_TYPES.includes(type) && (fee === '' || fee === undefined)) {
      newErrors.fee = t('addThing.priceRequired');
    }
    if (location.length > 32) newErrors.location = t('addThing.maxLocation');
    return newErrors;
  };

  // Errors surface only after the first submit attempt, then recompute on every
  // render so fixing a field clears its error immediately (live validation).
  const errors = submitAttempted ? computeErrors() : {};

  const handleSubmit = async () => {
    setSubmitAttempted(true);
    if (Object.keys(computeErrors()).length > 0) return;
    setSubmitting(true);
    setToast(null);

    const body = {
      type,
      headline: headline.trim(),
      collection_code: code,
    };
    if (thumbnail) body.thumbnail = thumbnail;
    if (description.trim()) body.description = description.trim();
    if (FEE_TYPES.includes(type) && fee !== '') {
      body.fee = fee;
    }
    if (DATE_TYPES.includes(type) && deposit !== '') {
      body.deposit = deposit;
    }
    if (DETAIL_TYPES.includes(type)) {
      if (availability) body.availability = availability;
      if (location.trim()) body.location = location.trim();
      if (condition) body.condition = condition;
    }
    if (gallery.length > 0) {
      body.gallery = gallery.map((g) => g.publicId);
    }
    if (tags.length > 0) {
      body.tags = tags;
    }
    if (['GIFT_THING', 'SELL_THING'].includes(type) && isEndless) {
      body.is_endless = true;
    }
    try {
      const res = await apiFetch('/api/v1/things/', {
        method: 'POST',
        body: JSON.stringify(body),
      });
      if (res.ok) {
        navigate(`/collections/${code}`);
      } else if (res.status === 429) {
        setToast({ type: 'error', message: t('common.tooManyAttempts') });
      } else {
        const detail = await extractApiError(res);
        setToast({ type: 'error', message: detail || t('addThing.errorCreating') });
      }
    } catch {
      setToast({ type: 'error', message: t('common.connectionError') });
    } finally {
      setSubmitting(false);
    }
  };

  // Theeeme colors from localStorage (set by HomePage on login)
  const { tc, btnStyle } = useTheeeme();

  const typeOptions = (() => {
    return TYPE_VALUES.filter((v) => {
      // Per-collection allowlist (set on Create/Edit). Empty = no restriction.
      if (collectionAllowedTypes.length > 0 && !collectionAllowedTypes.includes(v)) return false;
      // A type this COMMUNITY collection's owner explicitly allow-listed is open
      // to its invited members regardless of the deployment's own policy — an
      // empty allowlist is not "all", so this falls through to `isOfferable`.
      if (contributingToCommunity && collectionAllowedTypes.includes(v)) return true;
      // The deployment's own policy, which is a different question from the
      // owner's allowlist: that one is about this collection, this one is about
      // whether the account may offer the verb anywhere here at all.
      return isOfferable(capabilities, 'thing_types', v);
    });
  })().map((v) => ({ label: t('types.' + v), value: v }));
  // What the "needs approval" notice diffs against: the collection's own
  // allowlist applied, the deployment's policy not yet — except a type an
  // invited member may already contribute here is not withheld, so it drops out.
  const approvalCatalogue = TYPE_VALUES.filter(
    (v) => collectionAllowedTypes.length === 0 || collectionAllowedTypes.includes(v)
  )
    .filter((v) => !(contributingToCommunity && collectionAllowedTypes.includes(v)))
    .map((v) => ({ label: t('types.' + v), value: v }));

  return (
    <PageLayout
      backTo={`/collections/${code}`}
      backLabel={L(collectionHeadline) || t('common.collection')}
    >
      <h1 className="page-title-xl">{t('addThing.pageTitle')}</h1>
      <div className="form-grid">
        <ThingForm
          idPrefix="add-thing"
          theeemeColor01={tc.color_01}
          errors={errors}
          typeOptions={typeOptions}
          typeCatalogue={approvalCatalogue}
          showTypeSelector
          type={type}
          setType={setType}
          isEndless={isEndless}
          setIsEndless={setIsEndless}
          headline={headline}
          setHeadline={setHeadline}
          description={description}
          setDescription={setDescription}
          fee={fee}
          setFee={setFee}
          deposit={deposit}
          setDeposit={setDeposit}
          availability={availability}
          setAvailability={setAvailability}
          condition={condition}
          setCondition={setCondition}
          location={location}
          setLocation={setLocation}
          collectionTags={collectionTags}
          tags={tags}
          setTags={setTags}
          imageLabel={t('upload.thumbnailLabel')}
          thumbnail={thumbnail}
          setThumbnail={setThumbnail}
          gallery={gallery}
          setGallery={setGallery}
        />
      </div>

      <div className="form-actions">
        <Button style={{ ...btnStyle, width: '100%' }} disabled={submitting} onClick={handleSubmit}>
          {submitting ? t('common.creating') : t('common.create')}
        </Button>
      </div>

      <section id="bulk-add" className="bulk-add-section">
        <h2>{t('bulkAdd.heading')}</h2>
        <BulkAddCsv collectionCode={code} onImported={() => navigate(`/collections/${code}`)} />
      </section>

      <Toast toast={toast} onClose={() => setToast(null)} />
    </PageLayout>
  );
}
