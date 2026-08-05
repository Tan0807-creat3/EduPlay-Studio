namespace EduPlayPowerPointAddin.Core.Tests;

public sealed class HtmlFrameLayoutTests
{
    [Fact]
    public void CalculateAutoFitScale_ShrinksContentToFitViewport()
    {
        var scale = HtmlFrameLayout.CalculateAutoFitScale(
            contentWidth: 1600,
            contentHeight: 900,
            viewportWidth: 800,
            viewportHeight: 600);

        Assert.Equal(0.5, scale, 3);
    }

    [Fact]
    public void CalculateAutoFitScale_GrowsContentWhenViewportIsLarger()
    {
        var scale = HtmlFrameLayout.CalculateAutoFitScale(
            contentWidth: 800,
            contentHeight: 600,
            viewportWidth: 1600,
            viewportHeight: 1200);

        Assert.Equal(2.0, scale, 3);
    }

    [Fact]
    public void ResolveFrameSize_UsesRequestedDimensionsWhenTheyFit()
    {
        var size = HtmlFrameLayout.ResolveFrameSize(
            slideWidth: 1280,
            slideHeight: 720,
            requestedWidth: 900,
            requestedHeight: 500);

        Assert.Equal(900f, size.Width);
        Assert.Equal(500f, size.Height);
    }

    [Fact]
    public void ResolveFrameSize_ClampsRequestedDimensionsToSlideBounds()
    {
        var size = HtmlFrameLayout.ResolveFrameSize(
            slideWidth: 1280,
            slideHeight: 720,
            requestedWidth: 1400,
            requestedHeight: 900);

        Assert.Equal(1216f, size.Width);
        Assert.Equal(684f, size.Height);
    }
}
