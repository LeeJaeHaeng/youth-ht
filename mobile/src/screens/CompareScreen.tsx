import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, ScrollView, StyleSheet, Text, View } from 'react-native';
import { getCompare } from '../api/client';
import { Card, ScoreBar, Tag } from '../components';
import { colors, font, radius, spacing } from '../theme';
import type { RecommendItem, RootStackParamList } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'Compare'>;

const SCORE_DEFS = [
  { key: 'score_burden', label: 'H+T 부담', weight: 0.40, color: colors.scoreBurden },
  { key: 'score_commute', label: '통근', weight: 0.30, color: colors.scoreCommute },
  { key: 'score_safety', label: '안전', weight: 0.20, color: colors.scoreSafety },
  { key: 'score_future', label: '미래변화', weight: 0.10, color: colors.scoreFuture },
] as const;

function ColHeader({ item, side }: { item: RecommendItem; side: 'A' | 'B' }) {
  const sideColor = side === 'A' ? colors.primary : colors.scoreCommute;
  return (
    <View style={[s.colHeader, { borderTopColor: sideColor }]}>
      <View style={[s.sideBadge, { backgroundColor: sideColor }]}>
        <Text style={s.sideBadgeText}>{side}</Text>
      </View>
      <Text style={s.colRegion} numberOfLines={2}>{item.region_name}</Text>
      <Text style={s.colScore}>{item.total_score.toFixed(0)}<Text style={s.colScoreUnit}>점</Text></Text>
    </View>
  );
}

type Delta = 'better' | 'worse' | 'equal';

function deltaColor(d: Delta): string {
  return d === 'better' ? colors.success : d === 'worse' ? colors.danger : colors.textMuted;
}

function deltaText(d: Delta): string {
  return d === 'better' ? '✓' : d === 'worse' ? '▲' : '–';
}

function CompareRow({
  label,
  aVal,
  bVal,
  aDelta,
  bDelta,
}: {
  label: string;
  aVal: string;
  bVal: string;
  aDelta: Delta;
  bDelta: Delta;
}) {
  return (
    <View style={s.cmpRow}>
      <Text style={[s.cmpVal, { color: deltaColor(aDelta) }]}>{aVal}</Text>
      <View style={s.cmpLabelWrap}>
        <Text style={s.cmpLabel}>{label}</Text>
      </View>
      <Text style={[s.cmpVal, { color: deltaColor(bDelta), textAlign: 'right' }]}>{bVal}</Text>
    </View>
  );
}

function winningSide(a: number, b: number, lowerIsBetter = false): [Delta, Delta] {
  const diff = a - b;
  if (Math.abs(diff) < 0.001) return ['equal', 'equal'];
  const aWins = lowerIsBetter ? diff < 0 : diff > 0;
  return aWins ? ['better', 'worse'] : ['worse', 'better'];
}

function VerdictCard({ items }: { items: [RecommendItem, RecommendItem] }) {
  const [a, b] = items;
  const aWins = a.total_score > b.total_score;
  const scoreDiff = Math.abs(a.total_score - b.total_score).toFixed(1);
  const winner = aWins ? a : b;
  const loser = aWins ? b : a;

  const rentDiff = Math.abs(a.rent_mean_won - b.rent_mean_won) / 10000;
  const commuteDiff = Math.abs(a.commute_min - b.commute_min);
  const burdenDiff = Math.abs(a.burden_ratio - b.burden_ratio) * 100;

  return (
    <Card style={s.verdictCard}>
      <Text style={s.verdictTitle}>종합 분석</Text>
      <View style={[s.verdictBadge, { backgroundColor: aWins ? colors.primaryPale : colors.bgMuted }]}>
        <Text style={[s.verdictWinner, { color: aWins ? colors.primary : colors.scoreCommute }]}>
          {winner.region_name} 추천
        </Text>
        <Text style={s.verdictDiff}>종합점수 {scoreDiff}점 앞섬</Text>
      </View>

      <Text style={s.verdictBody}>
        {rentDiff >= 5
          ? `월세는 ${loser.region_name}이(가) ${rentDiff.toFixed(0)}만원 저렴하지만, `
          : '월세 차이는 크지 않으며, '}
        {commuteDiff >= 10
          ? `통근시간은 ${winner.region_name}이(가) ${commuteDiff}분 단축됩니다. `
          : '통근시간 차이도 크지 않습니다. '}
        {burdenDiff >= 2
          ? `H+T 부담률은 ${burdenDiff.toFixed(1)}%p 차이로, 장기적 재정 부담에 영향이 있습니다.`
          : '두 지역의 H+T 부담률은 유사합니다.'}
      </Text>

      <View style={s.verdictScores}>
        {SCORE_DEFS.map(({ key, label, color }) => {
          const aScore = (a[key as keyof RecommendItem] as number) * 100;
          const bScore = (b[key as keyof RecommendItem] as number) * 100;
          const diff = aScore - bScore;
          return (
            <View key={key} style={s.verdictScoreRow}>
              <Text style={[s.verdictScoreLabel, { color }]}>{label}</Text>
              <Text style={s.verdictScoreDiff}>
                {diff > 0 ? 'A +' : diff < 0 ? 'B +' : '동일 '}
                {Math.abs(diff).toFixed(0)}점
              </Text>
            </View>
          );
        })}
      </View>
    </Card>
  );
}

export default function CompareScreen({ route }: Props) {
  const { items, request } = route.params;
  const [a, b] = items;
  const [aiReport, setAiReport] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(true);
  const [aiError, setAiError] = useState<string | null>(null);

  useEffect(() => {
    getCompare(items, request)
      .then(setAiReport)
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : String(e);
        setAiError(msg);
        Alert.alert('AI 분석 오류', msg);
      })
      .finally(() => setAiLoading(false));
  }, []);

  const [rentDA, rentDB] = winningSide(a.rent_mean_won, b.rent_mean_won, true);
  const [comDA, comDB] = winningSide(a.commute_min, b.commute_min, true);
  const [burDA, burDB] = winningSide(a.burden_ratio, b.burden_ratio, true);
  const [hugDA, hugDB] = winningSide(a.hug_acc_rate_pct, b.hug_acc_rate_pct, true);
  const [futDA, futDB] = winningSide(a.future_burden_6m_ratio, b.future_burden_6m_ratio, true);
  const [scoreDA, scoreDB] = winningSide(a.total_score, b.total_score, false);

  return (
    <ScrollView style={s.container} contentContainerStyle={s.content} showsVerticalScrollIndicator={false}>

      {/* 헤더 */}
      <View style={s.header}>
        <ColHeader item={a} side="A" />
        <View style={s.headerDivider} />
        <ColHeader item={b} side="B" />
      </View>

      {/* 종합 분석 카드 */}
      <VerdictCard items={items} />

      {/* 핵심 지표 비교 */}
      <Card style={s.section}>
        <Text style={s.sectionTitle}>핵심 지표 비교</Text>
        <CompareRow
          label="종합 점수"
          aVal={a.total_score.toFixed(0) + '점'}
          bVal={b.total_score.toFixed(0) + '점'}
          aDelta={scoreDA} bDelta={scoreDB}
        />
        <CompareRow
          label="월 평균 월세"
          aVal={Math.round(a.rent_mean_won / 10000) + '만원'}
          bVal={Math.round(b.rent_mean_won / 10000) + '만원'}
          aDelta={rentDA} bDelta={rentDB}
        />
        <CompareRow
          label="H+T 부담률"
          aVal={(a.burden_ratio * 100).toFixed(1) + '%'}
          bVal={(b.burden_ratio * 100).toFixed(1) + '%'}
          aDelta={burDA} bDelta={burDB}
        />
        <CompareRow
          label="6개월 후 부담률"
          aVal={(a.future_burden_6m_ratio * 100).toFixed(1) + '%'}
          bVal={(b.future_burden_6m_ratio * 100).toFixed(1) + '%'}
          aDelta={futDA} bDelta={futDB}
        />
        <CompareRow
          label="통근 시간"
          aVal={a.commute_min + '분'}
          bVal={b.commute_min + '분'}
          aDelta={comDA} bDelta={comDB}
        />
        <CompareRow
          label="전세사기 위험 (HUG)"
          aVal={a.hug_acc_rate_pct.toFixed(1) + '%'}
          bVal={b.hug_acc_rate_pct.toFixed(1) + '%'}
          aDelta={hugDA} bDelta={hugDB}
        />
      </Card>

      {/* 점수 바 비교 */}
      <Card style={s.section}>
        <Text style={s.sectionTitle}>평가 점수 비교</Text>
        {SCORE_DEFS.map(({ key, label, color, weight }) => (
          <View key={key} style={s.barGroup}>
            <Text style={[s.barGroupLabel, { color }]}>{label} <Text style={s.barWeight}>w={weight}</Text></Text>
            <View style={s.barPair}>
              <Text style={s.barSide}>A</Text>
              <View style={s.barWrap}>
                <ScoreBar label="" value={a[key as keyof RecommendItem] as number} color={color} />
              </View>
            </View>
            <View style={s.barPair}>
              <Text style={s.barSide}>B</Text>
              <View style={s.barWrap}>
                <ScoreBar label="" value={b[key as keyof RecommendItem] as number} color={colors.scoreCommute} />
              </View>
            </View>
          </View>
        ))}
      </Card>

      {/* 신뢰도 비교 */}
      <Card style={s.section}>
        <Text style={s.sectionTitle}>신뢰도 비교</Text>
        <View style={s.confRow}>
          <View style={s.confBox}>
            <Text style={s.confNum}>{a.confidence}</Text>
            <Text style={s.confLabel}>A 신뢰도</Text>
            <Tag
              label={a.confidence >= 70 ? '높음' : a.confidence >= 40 ? '보통' : '낮음'}
              variant={a.confidence >= 70 ? 'success' : a.confidence >= 40 ? 'warning' : 'danger'}
              size="md"
            />
          </View>
          <View style={s.confDivider} />
          <View style={s.confBox}>
            <Text style={s.confNum}>{b.confidence}</Text>
            <Text style={s.confLabel}>B 신뢰도</Text>
            <Tag
              label={b.confidence >= 70 ? '높음' : b.confidence >= 40 ? '보통' : '낮음'}
              variant={b.confidence >= 70 ? 'success' : b.confidence >= 40 ? 'warning' : 'danger'}
              size="md"
            />
          </View>
        </View>
        {Math.abs(a.confidence - b.confidence) >= 20 && (
          <View style={s.confWarn}>
            <Text style={s.confWarnText}>
              ⚠️ 신뢰도 차이가 {Math.abs(a.confidence - b.confidence)}점으로 큽니다.
              신뢰도가 낮은 쪽은 데이터 부족으로 추천 정확도가 낮을 수 있습니다.
            </Text>
          </View>
        )}
      </Card>

      {/* AI 비교 분석 */}
      <Card style={s.section}>
        <View style={s.aiHeader}>
          <Text style={s.sectionTitle}>AI 비교 분석</Text>
          <View style={s.aiModelBadge}>
            <Text style={s.aiModelText}>✨ Gemini 2.5 Flash</Text>
          </View>
        </View>
        {aiLoading ? (
          <View style={s.aiLoading}>
            <ActivityIndicator color={colors.primary} size="large" />
            <Text style={s.aiLoadingText}>AI가 두 지역을 비교 분석 중…</Text>
          </View>
        ) : aiError ? (
          <View style={s.aiError}>
            <Text style={s.aiErrorIcon}>⚠️</Text>
            <Text style={s.aiErrorText}>{aiError}</Text>
          </View>
        ) : (
          <View style={s.aiReport}>
            <View style={s.aiQuote} />
            <Text style={s.aiReportText}>{aiReport}</Text>
          </View>
        )}
      </Card>

      <View style={{ height: 32 }} />
    </ScrollView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { paddingBottom: 48 },

  header: {
    flexDirection: 'row',
    backgroundColor: colors.bgCard,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
  },
  colHeader: {
    flex: 1, padding: spacing.md, alignItems: 'center',
    borderTopWidth: 4,
  },
  headerDivider: { width: 1, backgroundColor: colors.borderLight },
  sideBadge: {
    width: 32, height: 32, borderRadius: radius.full,
    justifyContent: 'center', alignItems: 'center', marginBottom: 8,
  },
  sideBadgeText: { color: '#fff', fontWeight: '800', fontSize: 16 },
  colRegion: { ...font.bodyBold, textAlign: 'center', marginBottom: 6 },
  colScore: { fontSize: 28, fontWeight: '800', color: colors.text },
  colScoreUnit: { fontSize: 14, fontWeight: '600', color: colors.textMuted },

  section: { margin: 12, marginBottom: 0 },
  sectionTitle: { ...font.h3, marginBottom: 14 },

  // 비교 행
  cmpRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
    gap: 6,
  },
  cmpVal: { flex: 1, fontSize: 14, fontWeight: '700' },
  cmpLabelWrap: { flex: 1, alignItems: 'center' },
  cmpLabel: { ...font.caption, color: colors.textSecondary, textAlign: 'center' },

  // 종합 분석
  verdictCard: { margin: 12, marginBottom: 0 },
  verdictTitle: { ...font.h3, marginBottom: 12 },
  verdictBadge: {
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: 12,
    alignItems: 'center',
  },
  verdictWinner: { fontSize: 18, fontWeight: '800', marginBottom: 4 },
  verdictDiff: { ...font.caption, color: colors.textSecondary },
  verdictBody: { ...font.body, lineHeight: 24, color: colors.text, marginBottom: 16 },
  verdictScores: { gap: 6 },
  verdictScoreRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  verdictScoreLabel: { ...font.caption, fontWeight: '700' },
  verdictScoreDiff: { ...font.caption, color: colors.textSecondary },

  // 점수 바 그룹
  barGroup: { marginBottom: 12 },
  barGroupLabel: { ...font.caption, fontWeight: '700', marginBottom: 4 },
  barWeight: { color: colors.textMuted, fontWeight: '400' },
  barPair: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 2 },
  barSide: { width: 14, fontSize: 11, fontWeight: '700', color: colors.textMuted },
  barWrap: { flex: 1 },

  // 신뢰도
  confRow: { flexDirection: 'row', alignItems: 'center' },
  confBox: { flex: 1, alignItems: 'center', paddingVertical: 12, gap: 6 },
  confDivider: { width: 1, height: 60, backgroundColor: colors.borderLight },
  confNum: { fontSize: 32, fontWeight: '800', color: colors.primary },
  confLabel: { ...font.caption, color: colors.textSecondary },
  confWarn: {
    backgroundColor: colors.warningLight,
    borderRadius: radius.md,
    padding: spacing.sm,
    marginTop: 12,
  },
  confWarnText: { fontSize: 12, color: colors.warning, lineHeight: 18 },

  // AI 비교 분석
  aiHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  aiModelBadge: {
    backgroundColor: colors.primaryPale, borderRadius: radius.full,
    paddingHorizontal: 10, paddingVertical: 3,
  },
  aiModelText: { fontSize: 11, color: colors.primary, fontWeight: '600' },
  aiLoading: { alignItems: 'center', paddingVertical: 24, gap: 10 },
  aiLoadingText: { ...font.bodyBold, color: colors.text },
  aiError: {
    backgroundColor: colors.dangerLight, borderRadius: radius.md,
    padding: spacing.md, alignItems: 'center', gap: 8,
  },
  aiErrorIcon: { fontSize: 24 },
  aiErrorText: { fontSize: 13, color: colors.danger, textAlign: 'center', lineHeight: 20 },
  aiReport: { flexDirection: 'row', gap: 10 },
  aiQuote: { width: 3, backgroundColor: colors.primary, borderRadius: 2, flexShrink: 0 },
  aiReportText: { ...font.body, flex: 1, lineHeight: 26, color: colors.text },
});
