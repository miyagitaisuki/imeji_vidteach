import { loadFont as loadBVP } from "@remotion/google-fonts/BeVietnamPro";
import { loadFont as loadNoto } from "@remotion/google-fonts/NotoSansJP";

export const loadBrandFonts = () => {
  loadBVP("normal", { weights: ["400", "500", "600", "700", "800"], subsets: ["vietnamese", "latin"] });
  loadNoto("normal", { weights: ["400", "500", "700"], ignoreTooManyRequestsWarning: true });
};
