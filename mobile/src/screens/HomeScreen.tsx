import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import React, { useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { recommend } from '../api/client';
import { Button, WeightSlider } from '../components';
import type { WeightValues } from '../components';
import { colors, font, radius, shadow, spacing } from '../theme';
import type { RootStackParamList } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

const PRESETS = [
  { name: '강남역', lat: 37.498, lng: 127.028, emoji: '🏢' },
  { name: '여의도', lat: 37.522, lng: 126.924, emoji: '💼' },
  { name: '판교', lat: 37.394, lng: 127.111, emoji: '💻' },
  { name: '마포/홍대', lat: 37.556, lng: 126.923, emoji: '🎨' },
  { name: '구로디지털', lat: 37.485, lng: 126.901, emoji: '🔧' },
  { name: '잠실/송파', lat: 37.513, lng: 127.100, emoji: '🏟️' },
];

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <View style={s.sectionHeader}>
      <Text style={s.sectionTitle}>{title}</Text>
      {subtitle && <Text style={s.sectionSub}>{subtitle}</Text>}
    </View>
  );
}

function InputField({
  label,
  value,
  onChangeText,
  placeholder,
  keyboardType = 'default',
  suffix,
  hint,
}: {
  label: string;
  value: string;
  onChangeText: (v: string) => void;
  placeholder: string;
  keyboardType?: 'default' | 'numeric' | 'decimal-pad';
  suffix?: string;
  hint?: string;
}) {
  return (
    <View style={s.fieldWrap}>
      <Text style={s.fieldLabel}>{label}</Text>
      <View style={s.inputRow}>
        <TextInput
          style={[s.input, suffix ? { flex: 1 } : {}]}
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={colors.textMuted}
          keyboardType={keyboardType}
        />
        {suffix && <Text style={s.inputSuffix}>{suffix}</Text>}
      </View>
      {hint && <Text style={s.fieldHint}>{hint}</Text>}
    </View>
  );
}

export default function HomeScreen({ navigation }: Props) {
  const [age, setAge] = useState('26');
  const [workName, setWorkName] = useState('');
  const [workLat, setWorkLat] = useState('');
  const [workLng, setWorkLng] = useState('');
  const [budgetWon, setBudgetWon] = useState('700000');
  const [commuteLimitMin, setCommuteLimitMin] = useState('60');
  const [weights, setWeights] = useState<WeightValues>({ burden: 40, commute: 30, safety: 20, future: 10 });
  const [showWeights, setShowWeights] = useState(false);
  const [loading, setLoading] = useState(false);

  const selectedPreset = PRESETS.find((p) => p.name === workName);

  function selectPreset(p: typeof PRESETS[0]) {
    setWorkName(p.name);
    setWorkLat(String(p.lat));
    setWorkLng(String(p.lng));
  }

  function budgetDisplay() {
    const n = parseInt(budgetWon || '0', 10);
    if (n >= 10000) return `${(n / 10000).toFixed(0)}만원`;
    return `${n.toLocaleString()}원`;
  }

  async function handleSubmit() {
    const ageNum = parseInt(age, 10);
    const lat = parseFloat(workLat);
    const lng = parseFloat(workLng);
    const budget = parseInt(budgetWon, 10);
    const commute = parseInt(commuteLimitMin, 10);

    if (!workName || isNaN(lat) || isNaN(lng)) {
      Alert.alert('직장 위치 필요', '위의 버튼으로 직장 클러스터를 선택하거나\n위도/경도를 직접 입력해주세요.');
      return;
    }
    if (isNaN(budget) || budget < 100000) {
      Alert.alert('예산 확인', '월세 예산을 10만원 이상으로 입력해주세요.');
      return;
    }

    setLoading(true);
    try {
      const total = weights.burden + weights.commute + weights.safety + weights.future;
      const req = {
        age: ageNum, work_lat: lat, work_lng: lng, work_name: workName,
        budget_won: budget, commute_limit_min: commute, top_n: 10,
        weight_burden: weights.burden / total,
        weight_commute: weights.commute / total,
        weight_safety: weights.safety / total,
        weight_future: weights.future / total,
      };
      const res = await recommend(req);
      navigation.navigate('Results', { response: res, request: req });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      Alert.alert('연결 오류', `FastAPI 서버에 연결할 수 없습니다.\n\n서버 실행 확인:\nuvicorn app.main:app --reload\n\n${msg}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView style={s.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>

        {/* 히어로 배너 */}
        <View style={s.hero}>
          <View style={s.heroBadge}>
            <Text style={s.heroBadgeText}>AI 기반 주거 추천</Text>
          </View>
          <Text style={s.heroTitle}>청년 안심{'\n'}H+T 추천</Text>
          <Text style={s.heroSub}>
            직장·예산·통근 조건으로{'\n'}최적 거주지를 찾아드립니다
          </Text>
          <View style={s.heroStats}>
            {[['113+', '시군구'], ['28,944', 'OD 쌍'], ['AI 3종', 'LGBM·GRU·Gemini']].map(([v, l]) => (
              <View key={l} style={s.heroStat}>
                <Text style={s.heroStatVal}>{v}</Text>
                <Text style={s.heroStatLabel}>{l}</Text>
              </View>
            ))}
          </View>
        </View>

        <View style={s.form}>

          {/* 나이 */}
          <SectionHeader title="기본 정보" />
          <InputField label="나이" value={age} onChangeText={setAge} placeholder="26" keyboardType="numeric" suffix="세" />

          {/* 직장 위치 */}
          <SectionHeader title="직장 위치" subtitle="주요 직장 밀집지역을 선택하세요" />
          <View style={s.presets}>
            {PRESETS.map((p) => (
              <TouchableOpacity
                key={p.name}
                style={[s.presetChip, selectedPreset?.name === p.name && s.presetChipActive]}
                onPress={() => selectPreset(p)}
                activeOpacity={0.75}
              >
                <Text style={s.presetEmoji}>{p.emoji}</Text>
                <Text style={[s.presetLabel, selectedPreset?.name === p.name && s.presetLabelActive]}>
                  {p.name}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={s.orDivider}>── 또는 직접 입력 ──</Text>

          <InputField
            label="직장명"
            value={workName}
            onChangeText={setWorkName}
            placeholder="예: 카카오 판교오피스"
          />
          <View style={s.coordRow}>
            <View style={s.flex}>
              <InputField
                label="위도"
                value={workLat}
                onChangeText={setWorkLat}
                placeholder="37.394"
                keyboardType="decimal-pad"
              />
            </View>
            <View style={{ width: 12 }} />
            <View style={s.flex}>
              <InputField
                label="경도"
                value={workLng}
                onChangeText={setWorkLng}
                placeholder="127.111"
                keyboardType="decimal-pad"
              />
            </View>
          </View>

          {/* 예산 */}
          <SectionHeader title="주거 조건" />
          <InputField
            label="월세 예산"
            value={budgetWon}
            onChangeText={setBudgetWon}
            placeholder="700000"
            keyboardType="numeric"
            suffix="원"
            hint={`입력값: ${budgetDisplay()}`}
          />
          <InputField
            label="최대 통근시간"
            value={commuteLimitMin}
            onChangeText={setCommuteLimitMin}
            placeholder="60"
            keyboardType="numeric"
            suffix="분"
            hint="자동차 기준 편도 통근시간"
          />

          {/* 가중치 설정 */}
          <View style={s.weightHeader}>
            <SectionHeader title="평가 가중치" subtitle="항목별 중요도를 직접 조정할 수 있습니다" />
            <TouchableOpacity onPress={() => setShowWeights(v => !v)} style={s.weightToggle}>
              <Text style={s.weightToggleText}>{showWeights ? '접기 ▲' : '조정 ▼'}</Text>
            </TouchableOpacity>
          </View>
          {!showWeights && (
            <View style={s.weightPreview}>
              {[
                { label: '부담 40%', color: colors.scoreBurden },
                { label: '통근 30%', color: colors.scoreCommute },
                { label: '안전 20%', color: colors.scoreSafety },
                { label: '미래 10%', color: colors.scoreFuture },
              ].map(({ label, color }) => (
                <View key={label} style={s.weightChip}>
                  <View style={[s.weightDot, { backgroundColor: color }]} />
                  <Text style={s.weightChipText}>{label}</Text>
                </View>
              ))}
            </View>
          )}
          {showWeights && (
            <WeightSlider values={weights} onChange={setWeights} />
          )}

          {/* 추천 버튼 */}
          <View style={s.submitWrap}>
            <Button
              label="안심 거주지 찾기"
              onPress={handleSubmit}
              loading={loading}
              size="lg"
              fullWidth
            />
            <Text style={s.submitHint}>LightGBM + GRU + Gemini AI 분석</Text>
          </View>

        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  flex: { flex: 1 },
  scroll: { backgroundColor: colors.bg, paddingBottom: 48 },

  // 히어로
  hero: {
    backgroundColor: colors.primary,
    paddingTop: 56,
    paddingBottom: 36,
    paddingHorizontal: spacing.lg,
  },
  heroBadge: {
    backgroundColor: 'rgba(255,255,255,0.20)',
    alignSelf: 'flex-start',
    borderRadius: radius.full,
    paddingHorizontal: 12,
    paddingVertical: 4,
    marginBottom: 16,
  },
  heroBadgeText: { color: '#fff', fontSize: 12, fontWeight: '600', letterSpacing: 0.5 },
  heroTitle: { color: '#fff', fontSize: 34, fontWeight: '800', letterSpacing: -0.8, lineHeight: 40 },
  heroSub: { color: 'rgba(255,255,255,0.80)', fontSize: 15, marginTop: 10, lineHeight: 22 },
  heroStats: {
    flexDirection: 'row',
    marginTop: 24,
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderRadius: radius.md,
    paddingVertical: 14,
    paddingHorizontal: spacing.md,
    gap: 0,
  },
  heroStat: { flex: 1, alignItems: 'center' },
  heroStatVal: { color: '#fff', fontSize: 17, fontWeight: '800' },
  heroStatLabel: { color: 'rgba(255,255,255,0.70)', fontSize: 11, marginTop: 2 },

  // 폼
  form: { padding: spacing.md, paddingTop: spacing.lg },
  sectionHeader: { marginTop: spacing.lg, marginBottom: spacing.sm },
  sectionTitle: { ...font.h3, color: colors.text },
  sectionSub: { ...font.caption, marginTop: 2 },

  // 직장 프리셋
  presets: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 4 },
  presetChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: radius.full,
    borderWidth: 1.5,
    borderColor: colors.border,
    backgroundColor: colors.bgCard,
    ...shadow.sm,
  },
  presetChipActive: {
    backgroundColor: colors.primaryPale,
    borderColor: colors.primary,
  },
  presetEmoji: { fontSize: 14 },
  presetLabel: { fontSize: 13, fontWeight: '500', color: colors.textSecondary },
  presetLabelActive: { color: colors.primary, fontWeight: '700' },

  orDivider: {
    textAlign: 'center',
    color: colors.textMuted,
    fontSize: 12,
    marginVertical: 12,
  },

  // 입력 필드
  fieldWrap: { marginBottom: spacing.sm },
  fieldLabel: { ...font.label, marginBottom: 5 },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.bgCard,
    ...shadow.sm,
  },
  input: {
    flex: 1,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    color: colors.text,
  },
  inputSuffix: {
    paddingRight: 14,
    fontSize: 14,
    color: colors.textMuted,
    fontWeight: '500',
  },
  fieldHint: { ...font.caption, marginTop: 4, color: colors.primary },
  coordRow: { flexDirection: 'row' },

  // 가중치
  weightHeader: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between' },
  weightToggle: {
    marginTop: spacing.lg + 2,
    paddingHorizontal: 12, paddingVertical: 5,
    borderRadius: radius.full,
    borderWidth: 1.5, borderColor: colors.border,
    backgroundColor: colors.bgCard,
  },
  weightToggleText: { fontSize: 12, fontWeight: '600', color: colors.textSecondary },
  weightPreview: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: spacing.sm },
  weightChip: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    paddingHorizontal: 10, paddingVertical: 5,
    borderRadius: radius.full, backgroundColor: colors.bgMuted,
  },
  weightDot: { width: 8, height: 8, borderRadius: 4 },
  weightChipText: { fontSize: 11, color: colors.textSecondary, fontWeight: '600' },

  // 제출 버튼
  submitWrap: { marginTop: spacing.xl, gap: 10 },
  submitHint: {
    textAlign: 'center',
    fontSize: 12,
    color: colors.textMuted,
    letterSpacing: 0.2,
  },
});
