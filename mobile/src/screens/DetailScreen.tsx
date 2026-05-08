import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { getReport } from '../api/client';
import { Card, ScoreBar, Tag } from '../components';
import { colors, font, radius, shadow, spacing } from '../theme';
import type { RootStackParamList } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'Detail'>;

function SectionTitle({ children }: { children: string }) {
  return <Text style={s.sectionTitle}>{children}</Text>;
}

function InfoRow({
  label,
  value,
  valueColor,
}: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <View style={s.infoRow}>
      <Text style={s.infoLabel}>{label}</Text>
      <Text style={[s.infoValue, valueColor ? { color: valueColor } : {}]}>{value}</Text>
    </View>
  );
}

function ScoreCard({
  label,
  score,
  weight,
  color,
}: {
  label: string;
  score: number;
  weight: number;
  color: string;
}) {
  const pct = Math.round(score * 100);
  return (
    <View style={[s.scoreCard, { borderTopColor: color }]}>
      <Text style={[s.scoreCardPct, { color }]}>{pct}</Text>
      <Text style={s.scoreCardLabel}>{label}</Text>
      <Text style={s.scoreCardWeight}>w={weight}</Text>
    </View>
  );
}

export default function DetailScreen({ route }: Props) {
  const { item, request } = route.params;
  const [report, setReport] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getReport(item, request)
      .then(setReport)
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : String(e);
        setError(msg);
        Alert.alert('AI 리포트 오류', msg);
      })
      .finally(() => setLoading(false));
  }, [item, request]);

  const hugColor =
    item.hug_acc_rate_pct > 3
      ? colors.danger
      : item.hug_acc_rate_pct > 1
      ? colors.warning
      : colors.success;

  const confTag =
    item.confidence >= 70 ? 'success' : item.confidence >= 40 ? 'warning' : 'danger';

  const burdenDelta =
    (item.future_burden_6m_ratio - item.burden_ratio) * 100;
  const burdenTrend = burdenDelta > 0.5 ? '📈 상승' : burdenDelta < -0.5 ? '📉 하락' : '➡️ 안정';

  return (
    <ScrollView style={s.container} contentContainerStyle={s.content} showsVerticalScrollIndicator={false}>

      {/* ── 히어로 카드 ── */}
      <View style={s.hero}>
        <View style={s.heroTop}>
          <View style={s.heroBadge}>
            <Text style={s.heroBadgeText}>#{item.rank} 추천</Text>
          </View>
          <Tag label={`신뢰도 ${item.confidence}`} variant={confTag} size="md" />
        </View>
        <Text style={s.heroRegion}>{item.region_name}</Text>
        <View style={s.heroScoreRow}>
          <View style={s.heroScoreBox}>
            <Text style={s.heroScoreNum}>{item.total_score.toFixed(0)}</Text>
            <Text style={s.heroScoreLabel}>종합 점수</Text>
          </View>
          <View style={s.heroDivider} />
          <View style={s.heroScoreBox}>
            <Text style={s.heroScoreNum}>{Math.round(item.rent_mean_won / 10000)}<Text style={s.heroUnit}>만</Text></Text>
            <Text style={s.heroScoreLabel}>월 평균 월세</Text>
          </View>
          <View style={s.heroDivider} />
          <View style={s.heroScoreBox}>
            <Text style={s.heroScoreNum}>{item.commute_min}<Text style={s.heroUnit}>분</Text></Text>
            <Text style={s.heroScoreLabel}>통근 시간</Text>
          </View>
        </View>
      </View>

      {/* ── 4대 점수 분해 ── */}
      <Card style={s.section}>
        <SectionTitle>평가 점수 분해</SectionTitle>
        <View style={s.scoreCards}>
          <ScoreCard label="H+T 부담" score={item.score_burden} weight={0.40} color={colors.scoreBurden} />
          <ScoreCard label="통근" score={item.score_commute} weight={0.30} color={colors.scoreCommute} />
          <ScoreCard label="안전" score={item.score_safety} weight={0.20} color={colors.scoreSafety} />
          <ScoreCard label="미래변화" score={item.score_future} weight={0.10} color={colors.scoreFuture} />
        </View>
        <View style={s.bars}>
          <ScoreBar label="부담" value={item.score_burden} color={colors.scoreBurden} />
          <ScoreBar label="통근" value={item.score_commute} color={colors.scoreCommute} />
          <ScoreBar label="안전" value={item.score_safety} color={colors.scoreSafety} />
          <ScoreBar label="미래" value={item.score_future} color={colors.scoreFuture} />
        </View>
      </Card>

      {/* ── 핵심 지표 ── */}
      <Card style={s.section}>
        <SectionTitle>핵심 지표</SectionTitle>
        <InfoRow label="월 평균 월세" value={`${Math.round(item.rent_mean_won / 10000)}만원`} valueColor={colors.primary} />
        <InfoRow label="평균 보증금" value={`${Math.round(item.deposit_mean_won / 10000)}만원`} />
        <InfoRow label="H+T 부담률 (현재)" value={`${(item.burden_ratio * 100).toFixed(1)}%`} />
        <InfoRow
          label="6개월 후 부담률"
          value={`${(item.future_burden_6m_ratio * 100).toFixed(1)}% ${burdenTrend}`}
          valueColor={burdenDelta > 0.5 ? colors.danger : burdenDelta < -0.5 ? colors.success : colors.text}
        />
        <InfoRow label="자동차 통근시간" value={`${item.commute_min}분`} />
        <InfoRow
          label="전세사기 위험 (HUG)"
          value={`${item.hug_acc_rate_pct.toFixed(1)}%`}
          valueColor={hugColor}
        />
        <View style={s.infoRow}>
          <Text style={s.infoLabel}>위험 등급</Text>
          <Tag
            label={item.hug_acc_rate_pct > 3 ? '⚠️ 주의' : item.hug_acc_rate_pct > 1 ? '보통' : '✅ 안심'}
            variant={item.hug_acc_rate_pct > 3 ? 'danger' : item.hug_acc_rate_pct > 1 ? 'warning' : 'success'}
            size="md"
          />
        </View>
      </Card>

      {/* ── AI 자연어 리포트 ── */}
      <Card style={s.section}>
        <View style={s.aiHeader}>
          <SectionTitle>AI 맞춤 리포트</SectionTitle>
          <View style={s.aiModelBadge}>
            <Text style={s.aiModelText}>✨ Gemini 2.5 Flash</Text>
          </View>
        </View>

        {loading ? (
          <View style={s.aiLoading}>
            <ActivityIndicator color={colors.primary} size="large" />
            <Text style={s.aiLoadingText}>AI가 맞춤 분석 중…</Text>
            <Text style={s.aiLoadingHint}>월세 추세 · 통근 패턴 · 위험 요소 종합</Text>
          </View>
        ) : error ? (
          <View style={s.aiError}>
            <Text style={s.aiErrorIcon}>⚠️</Text>
            <Text style={s.aiErrorText}>{error}</Text>
          </View>
        ) : (
          <View style={s.aiReport}>
            <View style={s.aiQuote} />
            <Text style={s.aiReportText}>{report}</Text>
          </View>
        )}
      </Card>

      {/* ── 신뢰도 세부 ── */}
      <Card style={s.section}>
        <SectionTitle>신뢰도 상세</SectionTitle>
        <Text style={s.confNote}>신뢰도는 데이터 품질·표본·AI 모델 수렴도를 종합합니다</Text>
        {Object.entries(item.confidence_breakdown).map(([key, val]) => (
          <InfoRow key={key} label={key} value={`${val}점`} />
        ))}
        <View style={s.confTotal}>
          <Text style={s.confTotalLabel}>총 신뢰도</Text>
          <Text style={s.confTotalVal}>{item.confidence} / 100</Text>
        </View>
      </Card>

      <View style={{ height: 24 }} />
    </ScrollView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { paddingBottom: 48 },

  // 히어로
  hero: {
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xl,
  },
  heroTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  heroBadge: {
    backgroundColor: 'rgba(255,255,255,0.22)',
    borderRadius: radius.full,
    paddingHorizontal: 12,
    paddingVertical: 4,
  },
  heroBadgeText: { color: '#fff', fontSize: 12, fontWeight: '600' },
  heroRegion: { color: '#fff', fontSize: 26, fontWeight: '800', letterSpacing: -0.5, marginBottom: 20 },
  heroScoreRow: {
    flexDirection: 'row',
    backgroundColor: 'rgba(255,255,255,0.14)',
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: 'center',
  },
  heroScoreBox: { flex: 1, alignItems: 'center' },
  heroScoreNum: { color: '#fff', fontSize: 26, fontWeight: '800', lineHeight: 30 },
  heroUnit: { fontSize: 14, fontWeight: '600' },
  heroScoreLabel: { color: 'rgba(255,255,255,0.72)', fontSize: 11, marginTop: 2 },
  heroDivider: { width: 1, height: 36, backgroundColor: 'rgba(255,255,255,0.25)' },

  // 공통 섹션
  section: { margin: 12, marginBottom: 0 },
  sectionTitle: { ...font.h3, marginBottom: 12 },

  // 점수 카드
  scoreCards: { flexDirection: 'row', gap: 6, marginBottom: 14 },
  scoreCard: {
    flex: 1,
    borderTopWidth: 3,
    borderRadius: radius.md,
    backgroundColor: colors.bgMuted,
    paddingVertical: 10,
    alignItems: 'center',
  },
  scoreCardPct: { fontSize: 20, fontWeight: '800' },
  scoreCardLabel: { fontSize: 10, color: colors.textSecondary, marginTop: 2, textAlign: 'center' },
  scoreCardWeight: { fontSize: 9, color: colors.textMuted, marginTop: 1 },
  bars: { gap: 3 },

  // 지표 행
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 9,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
  },
  infoLabel: { ...font.caption, color: colors.textSecondary, flex: 1 },
  infoValue: { ...font.bodyBold, color: colors.text },

  // AI 리포트
  aiHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  aiModelBadge: {
    backgroundColor: colors.primaryPale,
    borderRadius: radius.full,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  aiModelText: { fontSize: 11, color: colors.primary, fontWeight: '600' },
  aiLoading: { alignItems: 'center', paddingVertical: 28, gap: 10 },
  aiLoadingText: { ...font.bodyBold, color: colors.text },
  aiLoadingHint: { ...font.caption },
  aiError: {
    backgroundColor: colors.dangerLight,
    borderRadius: radius.md,
    padding: spacing.md,
    alignItems: 'center',
    gap: 8,
  },
  aiErrorIcon: { fontSize: 24 },
  aiErrorText: { fontSize: 13, color: colors.danger, textAlign: 'center', lineHeight: 20 },
  aiReport: { flexDirection: 'row', gap: 10 },
  aiQuote: {
    width: 3,
    backgroundColor: colors.primary,
    borderRadius: 2,
    flexShrink: 0,
  },
  aiReportText: { ...font.body, flex: 1, lineHeight: 26, color: colors.text },

  // 신뢰도
  confNote: { ...font.caption, marginBottom: 10, lineHeight: 18 },
  confTotal: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingTop: 12,
    marginTop: 4,
  },
  confTotalLabel: { ...font.bodyBold },
  confTotalVal: { fontSize: 18, fontWeight: '800', color: colors.primary },
});
