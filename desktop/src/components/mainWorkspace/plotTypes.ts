export type PlotType =
  | "f1_f2"
  | "f1_f2_minus_f1"
  | "f1_f3"
  | "f1_f2_prime"
  | "f1_f2_prime_minus_f1";

export const PLOT_TYPES: Array<{
  id: PlotType;
  label: string;
  description: string;
  short: string;
  needsF3?: boolean;
}> = [
  {
    id: "f1_f2",
    label: "기본 모음 공간",
    description: "F1과 F2로 가장 익숙한 모음 공간을 그립니다.",
    short: "F1·F2",
  },
  {
    id: "f1_f2_minus_f1",
    label: "청각적 거리",
    description: "F2−F1 차이로 모음 사이의 거리를 살펴봅니다.",
    short: "F1·F2−F1",
  },
  {
    id: "f1_f3",
    label: "제3포먼트 공간",
    description: "F1과 F3의 관계를 함께 살펴봅니다.",
    short: "F1·F3",
    needsF3: true,
  },
  {
    id: "f1_f2_prime",
    label: "유효 F2 공간",
    description: "F2′ 값을 사용해 지각적 모음 공간을 그립니다.",
    short: "F1·F2′",
    needsF3: true,
  },
  {
    id: "f1_f2_prime_minus_f1",
    label: "유효 F2 거리",
    description: "F2′−F1 차이로 지각적 거리를 살펴봅니다.",
    short: "F1·F2′−F1",
    needsF3: true,
  },
];

export const X_AXIS_LABEL: Record<PlotType, string> = {
  f1_f2: "F2",
  f1_f2_minus_f1: "F2 − F1",
  f1_f3: "F3",
  f1_f2_prime: "F2′",
  f1_f2_prime_minus_f1: "F2′ − F1",
};

export const scaleLabel = (value?: string) => {
  if (value === "log") return "로그";
  if (value === "bark") return "Bark";
  return "선형";
};
