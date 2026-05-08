// Claude Design System — 청년 안심 H+T

export const colors = {
  // Claude 브랜드 색상
  primary: '#DA7756',        // Claude 오렌지
  primaryDark: '#C0614A',
  primaryLight: '#F5DDD6',
  primaryPale: '#FDF6F3',

  // 배경
  bg: '#FAF9F6',             // 크림 배경
  bgCard: '#FFFFFF',
  bgMuted: '#F4F3EE',

  // 텍스트
  text: '#1A1A1A',
  textSecondary: '#5A5A5A',
  textMuted: '#9A9A9A',
  textInverted: '#FFFFFF',

  // 테두리
  border: '#E8E6DF',
  borderLight: '#F0EEE8',

  // 상태 색상
  success: '#2D7A4F',
  successLight: '#D4EDDF',
  warning: '#B45309',
  warningLight: '#FEF3C7',
  danger: '#C0392B',
  dangerLight: '#FDECEA',
  info: '#1D4ED8',
  infoLight: '#DBEAFE',

  // 점수 색상
  scoreBurden: '#DA7756',
  scoreCommute: '#7C3AED',
  scoreSafety: '#2D7A4F',
  scoreFuture: '#B45309',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  full: 9999,
};

export const font = {
  // 제목
  h1: { fontSize: 28, fontWeight: '700' as const, color: colors.text, letterSpacing: -0.5 },
  h2: { fontSize: 22, fontWeight: '700' as const, color: colors.text, letterSpacing: -0.3 },
  h3: { fontSize: 18, fontWeight: '600' as const, color: colors.text },
  // 본문
  body: { fontSize: 15, fontWeight: '400' as const, color: colors.text, lineHeight: 22 },
  bodyBold: { fontSize: 15, fontWeight: '600' as const, color: colors.text },
  // 보조
  caption: { fontSize: 12, fontWeight: '400' as const, color: colors.textSecondary },
  label: { fontSize: 13, fontWeight: '600' as const, color: colors.textSecondary, letterSpacing: 0.3 },
  // 숫자
  number: { fontSize: 24, fontWeight: '800' as const, color: colors.text },
  numberSm: { fontSize: 16, fontWeight: '700' as const, color: colors.text },
};

export const shadow = {
  sm: {
    shadowColor: '#1A1A1A',
    shadowOpacity: 0.06,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 1 },
    elevation: 1,
  },
  md: {
    shadowColor: '#1A1A1A',
    shadowOpacity: 0.08,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  lg: {
    shadowColor: '#1A1A1A',
    shadowOpacity: 0.10,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
};
