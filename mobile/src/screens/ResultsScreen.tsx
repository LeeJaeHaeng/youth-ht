import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import React, { useState } from 'react';
import {
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { Button, Card, ScoreBar, Tag } from '../components';
import { colors, font, radius, spacing } from '../theme';
import type { RecommendItem, RootStackParamList } from '../types';
import MapScreen from './MapScreen';

type Props = NativeStackScreenProps<RootStackParamList, 'Results'>;

function hugVariant(rate: number): 'success' | 'warning' | 'danger' {
  if (rate <= 1.0) return 'success';
  if (rate <= 3.0) return 'warning';
  return 'danger';
}

function confVariant(conf: number): 'success' | 'warning' | 'danger' {
  if (conf >= 70) return 'success';
  if (conf >= 40) return 'warning';
  return 'danger';
}

function MetricPill({ label, value, primary }: { label: string; value: string; primary?: boolean }) {
  return (
    <View style={[s.pill, primary && s.pillPrimary]}>
      <Text style={[s.pillLabel, primary && s.pillLabelPrimary]}>{label}</Text>
      <Text style={[s.pillValue, primary && s.pillValuePrimary]}>{value}</Text>
    </View>
  );
}

function RegionCard({
  item,
  onPress,
  isSelected,
  onToggleSelect,
  compareMode,
}: {
  item: RecommendItem;
  onPress: () => void;
  isSelected: boolean;
  onToggleSelect: () => void;
  compareMode: boolean;
}) {
  return (
    <Card onPress={onPress} elevated style={isSelected ? [s.card, s.cardSelected] : s.card}>
      <View style={s.cardTop}>
        {compareMode && (
          <TouchableOpacity
            style={[s.checkBox, isSelected && s.checkBoxActive]}
            onPress={(e) => { e.stopPropagation?.(); onToggleSelect(); }}
            activeOpacity={0.7}
          >
            {isSelected && <Text style={s.checkMark}>✓</Text>}
          </TouchableOpacity>
        )}
        <View style={s.rankCircle}>
          <Text style={s.rankText}>{item.rank}</Text>
        </View>
        <View style={s.cardTitleBlock}>
          <Text style={s.regionName} numberOfLines={1}>{item.region_name}</Text>
          <View style={s.tagRow}>
            <Tag label={`신뢰도 ${item.confidence}`} variant={confVariant(item.confidence)} />
            <Tag label={`HUG ${item.hug_acc_rate_pct.toFixed(1)}%`} variant={hugVariant(item.hug_acc_rate_pct)} />
          </View>
        </View>
        <View style={s.totalScoreBox}>
          <Text style={s.totalScoreNum}>{item.total_score.toFixed(0)}</Text>
          <Text style={s.totalScoreUnit}>점</Text>
        </View>
      </View>

      <View style={s.pillRow}>
        <MetricPill label="월세" value={`${Math.round(item.rent_mean_won / 10000)}만`} primary />
        <MetricPill label="통근" value={`${item.commute_min}분`} />
        <MetricPill label="부담" value={`${(item.burden_ratio * 100).toFixed(0)}%`} />
        <MetricPill label="6개월후" value={`${(item.future_burden_6m_ratio * 100).toFixed(0)}%`} />
      </View>

      <View style={s.bars}>
        <ScoreBar label="부담" value={item.score_burden} color={colors.scoreBurden} />
        <ScoreBar label="통근" value={item.score_commute} color={colors.scoreCommute} />
        <ScoreBar label="안전" value={item.score_safety} color={colors.scoreSafety} />
        <ScoreBar label="미래" value={item.score_future} color={colors.scoreFuture} />
      </View>

      <Text style={s.tapHint}>{compareMode ? (isSelected ? '✓ 선택됨' : '탭하여 선택') : 'AI 리포트 보기 →'}</Text>
    </Card>
  );
}

type ViewMode = 'list' | 'map';

export default function ResultsScreen({ navigation, route }: Props) {
  const { response, request } = route.params;
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [compareMode, setCompareMode] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);

  function toggleSelect(regionId: string) {
    setSelected(prev => {
      if (prev.includes(regionId)) return prev.filter(id => id !== regionId);
      if (prev.length >= 2) return [prev[1], regionId];
      return [...prev, regionId];
    });
  }

  function handleCompare() {
    if (selected.length !== 2) return;
    const itemA = response.items.find(i => i.region_id === selected[0])!;
    const itemB = response.items.find(i => i.region_id === selected[1])!;
    navigation.navigate('Compare', { items: [itemA, itemB], request });
  }

  function handleCardPress(item: RecommendItem) {
    if (compareMode) {
      toggleSelect(item.region_id);
    } else {
      navigation.navigate('Detail', { item, request });
    }
  }

  return (
    <View style={s.container}>
      {/* 서머리 헤더 */}
      <View style={s.summary}>
        <View style={s.summaryLeft}>
          <Text style={s.summaryWork}>{request.work_name}</Text>
          <Text style={s.summaryCondition}>
            예산 {Math.round(request.budget_won / 10000)}만원 · 통근 {request.commute_limit_min}분 이내
          </Text>
        </View>
        <View style={s.summaryBadge}>
          <Text style={s.summaryBadgeNum}>{response.items.length}</Text>
          <Text style={s.summaryBadgeLabel}>추천</Text>
        </View>
      </View>

      <View style={s.metaBar}>
        {/* 목록/지도 탭 */}
        <View style={s.tabToggle}>
          <TouchableOpacity
            style={[s.tabBtn, viewMode === 'list' && s.tabBtnActive]}
            onPress={() => setViewMode('list')}
          >
            <Text style={[s.tabBtnText, viewMode === 'list' && s.tabBtnTextActive]}>목록</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[s.tabBtn, viewMode === 'map' && s.tabBtnActive]}
            onPress={() => setViewMode('map')}
          >
            <Text style={[s.tabBtnText, viewMode === 'map' && s.tabBtnTextActive]}>지도</Text>
          </TouchableOpacity>
        </View>
        <Text style={s.metaText}>
          통과 {response.candidates_after_stage1}개 → Top {response.items.length}
        </Text>
        {viewMode === 'list' && (
          <TouchableOpacity
            onPress={() => { setCompareMode(v => !v); setSelected([]); }}
            style={[s.compareToggle, compareMode && s.compareToggleActive]}
          >
            <Text style={[s.compareToggleText, compareMode && s.compareToggleTextActive]}>
              {compareMode ? '취소' : '비교'}
            </Text>
          </TouchableOpacity>
        )}
      </View>

      {/* 비교 선택 배너 */}
      {compareMode && (
        <View style={s.compareBanner}>
          <Text style={s.compareBannerText}>
            {selected.length === 0
              ? '비교할 지역 2개를 선택하세요'
              : selected.length === 1
              ? '1개 선택됨 — 1개 더 선택하세요'
              : '2개 선택됨 — 비교 분석을 시작하세요'}
          </Text>
          {selected.length === 2 && (
            <Button
              label="비교 분석하기"
              onPress={handleCompare}
              size="sm"
            />
          )}
        </View>
      )}

      {response.items.length === 0 ? (
        <View style={s.empty}>
          <Text style={s.emptyIcon}>🔍</Text>
          <Text style={s.emptyTitle}>조건에 맞는 지역이 없습니다</Text>
          <Text style={s.emptySub}>예산 또는 통근 한계를 늘려서 다시 시도해보세요</Text>
        </View>
      ) : viewMode === 'map' ? (
        <MapScreen
          items={response.items}
          request={request}
          onCardPress={(item) => navigation.navigate('Detail', { item, request })}
        />
      ) : (
        <FlatList
          data={response.items}
          keyExtractor={(item) => item.region_id}
          renderItem={({ item }) => (
            <RegionCard
              item={item}
              onPress={() => handleCardPress(item)}
              isSelected={selected.includes(item.region_id)}
              onToggleSelect={() => toggleSelect(item.region_id)}
              compareMode={compareMode}
            />
          )}
          contentContainerStyle={s.list}
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },

  summary: {
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
    paddingBottom: spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
  },
  summaryLeft: { flex: 1 },
  summaryWork: { color: '#fff', fontSize: 18, fontWeight: '700' },
  summaryCondition: { color: 'rgba(255,255,255,0.80)', fontSize: 13, marginTop: 2 },
  summaryBadge: {
    backgroundColor: 'rgba(255,255,255,0.20)',
    borderRadius: radius.md,
    paddingHorizontal: 16,
    paddingVertical: 8,
    alignItems: 'center',
  },
  summaryBadgeNum: { color: '#fff', fontSize: 24, fontWeight: '800' },
  summaryBadgeLabel: { color: 'rgba(255,255,255,0.80)', fontSize: 11 },

  metaBar: {
    backgroundColor: colors.bgMuted,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  tabToggle: {
    flexDirection: 'row',
    backgroundColor: colors.border,
    borderRadius: radius.full,
    padding: 2,
  },
  tabBtn: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: radius.full,
  },
  tabBtnActive: { backgroundColor: colors.bgCard },
  tabBtnText: { fontSize: 12, fontWeight: '600', color: colors.textMuted },
  tabBtnTextActive: { color: colors.text },
  metaText: { ...font.caption, color: colors.textSecondary, flex: 1 },
  compareToggle: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: radius.full,
    borderWidth: 1.5,
    borderColor: colors.border,
  },
  compareToggleActive: { backgroundColor: colors.primaryPale, borderColor: colors.primary },
  compareToggleText: { fontSize: 12, fontWeight: '600', color: colors.textSecondary },
  compareToggleTextActive: { color: colors.primary },

  compareBanner: {
    backgroundColor: colors.primaryPale,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  compareBannerText: { fontSize: 13, color: colors.primaryDark, fontWeight: '500', flex: 1, marginRight: 8 },

  list: { padding: 12, paddingBottom: 32 },
  card: { marginBottom: 12 },
  cardSelected: { borderWidth: 2, borderColor: colors.primary },

  cardTop: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 12 },
  checkBox: {
    width: 24, height: 24, borderRadius: 6, borderWidth: 2,
    borderColor: colors.border, marginRight: 8, flexShrink: 0,
    justifyContent: 'center', alignItems: 'center',
    backgroundColor: colors.bgCard,
  },
  checkBoxActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  checkMark: { color: '#fff', fontSize: 14, fontWeight: '800' },

  rankCircle: {
    width: 36, height: 36, borderRadius: 18,
    backgroundColor: colors.primaryPale,
    justifyContent: 'center', alignItems: 'center',
    marginRight: 10, flexShrink: 0,
  },
  rankText: { color: colors.primary, fontSize: 16, fontWeight: '800' },
  cardTitleBlock: { flex: 1 },
  regionName: { ...font.bodyBold, color: colors.text, marginBottom: 5 },
  tagRow: { flexDirection: 'row', gap: 5 },

  totalScoreBox: { alignItems: 'center', marginLeft: 8 },
  totalScoreNum: { fontSize: 26, fontWeight: '800', color: colors.text, lineHeight: 28 },
  totalScoreUnit: { fontSize: 11, color: colors.textMuted, marginTop: -2 },

  pillRow: { flexDirection: 'row', gap: 6, marginBottom: 10 },
  pill: {
    flex: 1, alignItems: 'center', paddingVertical: 8, paddingHorizontal: 4,
    borderRadius: radius.md, backgroundColor: colors.bgMuted,
  },
  pillPrimary: { backgroundColor: colors.primaryPale },
  pillLabel: { fontSize: 10, color: colors.textMuted, fontWeight: '500' },
  pillLabelPrimary: { color: colors.primaryDark },
  pillValue: { fontSize: 14, fontWeight: '700', color: colors.text, marginTop: 2 },
  pillValuePrimary: { color: colors.primary },

  bars: { gap: 2 },
  tapHint: { ...font.caption, textAlign: 'right', marginTop: 8, color: colors.primary },

  empty: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 40 },
  emptyIcon: { fontSize: 48, marginBottom: 16 },
  emptyTitle: { ...font.h3, textAlign: 'center' },
  emptySub: { ...font.caption, textAlign: 'center', marginTop: 8, lineHeight: 20 },
});
