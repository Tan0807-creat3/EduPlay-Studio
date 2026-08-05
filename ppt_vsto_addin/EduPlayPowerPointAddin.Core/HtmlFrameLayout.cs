using System;

namespace EduPlayPowerPointAddin.Core
{
    public struct HtmlFrameSize
    {
        public HtmlFrameSize(float width, float height)
        {
            Width = width;
            Height = height;
        }

        public float Width { get; }

        public float Height { get; }
    }

    public static class HtmlFrameLayout
    {
        private const float DefaultWidthRatio = 0.8f;
        private const float DefaultHeightRatio = 0.6f;
        private const float DefaultMaxWidth = 720f;
        private const float DefaultMaxHeight = 405f;
        private const float RequestedMaxRatio = 0.95f;

        public static HtmlFrameSize ResolveFrameSize(
            float slideWidth,
            float slideHeight,
            float? requestedWidth = null,
            float? requestedHeight = null)
        {
            var safeSlideWidth = Math.Max(1f, slideWidth);
            var safeSlideHeight = Math.Max(1f, slideHeight);
            var maxWidth = Math.Max(1f, safeSlideWidth * RequestedMaxRatio);
            var maxHeight = Math.Max(1f, safeSlideHeight * RequestedMaxRatio);

            if (requestedWidth.HasValue || requestedHeight.HasValue)
            {
                var width = Clamp(requestedWidth ?? Math.Min(DefaultMaxWidth, safeSlideWidth * DefaultWidthRatio), 1f, maxWidth);
                var height = Clamp(requestedHeight ?? Math.Min(DefaultMaxHeight, safeSlideHeight * DefaultHeightRatio), 1f, maxHeight);
                return new HtmlFrameSize(width, height);
            }

            var defaultWidth = Math.Min(DefaultMaxWidth, safeSlideWidth * DefaultWidthRatio);
            var defaultHeight = Math.Min(DefaultMaxHeight, safeSlideHeight * DefaultHeightRatio);
            return new HtmlFrameSize(defaultWidth, defaultHeight);
        }

        public static double CalculateAutoFitScale(
            double contentWidth,
            double contentHeight,
            double viewportWidth,
            double viewportHeight)
        {
            if (contentWidth <= 0 || contentHeight <= 0 || viewportWidth <= 0 || viewportHeight <= 0)
            {
                return 1d;
            }

            var widthScale = viewportWidth / contentWidth;
            var heightScale = viewportHeight / contentHeight;
            return Math.Min(widthScale, heightScale);
        }

        private static float Clamp(float value, float minValue, float maxValue)
        {
            return Math.Min(Math.Max(value, minValue), maxValue);
        }
    }
}
