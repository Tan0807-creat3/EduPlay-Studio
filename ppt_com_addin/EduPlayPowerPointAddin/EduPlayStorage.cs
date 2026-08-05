using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Xml.Linq;
using PowerPoint = Microsoft.Office.Interop.PowerPoint;

namespace EduPlay.PowerPointAddin;

internal sealed class EduPlayStorage
{
    private const string NamespaceUri = "urn:eduplay:embedded-html";
    private const int ChunkChars = 900_000;

    private readonly PowerPoint.Presentation _presentation;

    public EduPlayStorage(PowerPoint.Presentation presentation)
    {
        _presentation = presentation ?? throw new ArgumentNullException(nameof(presentation));
    }

    public bool HasSlideData(int slideId)
    {
        try
        {
            return TryLoadSlideHtml(slideId, out _);
        }
        catch
        {
            return false;
        }
    }

    public void SaveSlideHtml(int slideId, string html)
    {
        var key = SlideKey(slideId);
        DeleteByKey(key);

        var bytes = Encoding.UTF8.GetBytes(html ?? "");
        var gz = Gzip(bytes);
        var b64 = Convert.ToBase64String(gz);

        var chunks = SplitChunks(b64, ChunkChars).ToList();
        if (chunks.Count == 0)
        {
            chunks.Add("");
        }

        for (var i = 0; i < chunks.Count; i++)
        {
            var xml = new XDocument(
                new XElement(
                    XName.Get("eduplay", NamespaceUri),
                    new XAttribute("key", key),
                    new XAttribute("idx", i),
                    new XAttribute("total", chunks.Count),
                    new XAttribute("codec", "gzip+b64"),
                    new XCData(chunks[i] ?? "")
                )
            );
            _presentation.CustomXMLParts.Add(xml.ToString(SaveOptions.DisableFormatting));
        }
    }

    public bool TryLoadSlideHtml(int slideId, out string html)
    {
        html = "";
        var key = SlideKey(slideId);

        var parts = GetPartsByKey(key)
            .Select(p => new { Part = p, Doc = SafeParse(p.XML) })
            .Where(x => x.Doc != null)
            .Select(x => new { x.Part, Root = x.Doc!.Root })
            .Where(x => x.Root != null && string.Equals((string?)x.Root!.Attribute("key"), key, StringComparison.OrdinalIgnoreCase))
            .Select(x => new
            {
                idx = SafeInt((string?)x.Root!.Attribute("idx")),
                total = SafeInt((string?)x.Root!.Attribute("total")),
                codec = (string?)x.Root!.Attribute("codec") ?? "",
                data = x.Root!.Value ?? ""
            })
            .ToList();

        if (parts.Count == 0)
        {
            return false;
        }

        parts.Sort((a, b) => a.idx.CompareTo(b.idx));
        var expected = parts.Max(p => p.total);
        if (expected > 0 && parts.Count < expected)
        {
            return false;
        }

        var merged = string.Concat(parts.Select(p => p.data));
        var raw = Convert.FromBase64String(merged);
        var unz = Gunzip(raw);
        html = Encoding.UTF8.GetString(unz);
        return !string.IsNullOrWhiteSpace(html);
    }

    public string MaterializeTempFile(int slideId)
    {
        if (!TryLoadSlideHtml(slideId, out var html) || string.IsNullOrWhiteSpace(html))
        {
            return "";
        }

        var presId = "";
        try
        {
            presId = string.IsNullOrWhiteSpace(_presentation?.FullName) ? "" : _presentation.FullName;
        }
        catch
        {
            presId = "";
        }

        var dir = Path.Combine(Path.GetTempPath(), "EduPlayPPT", HashText(presId));
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, $"slide_{slideId}.html");
        File.WriteAllText(path, html, Encoding.UTF8);
        return path;
    }

    private IEnumerable<PowerPoint.CustomXMLPart> GetPartsByKey(string key)
    {
        var list = new List<PowerPoint.CustomXMLPart>();
        foreach (PowerPoint.CustomXMLPart part in _presentation.CustomXMLParts)
        {
            var xml = "";
            try { xml = part.XML; } catch { xml = ""; }
            if (xml.IndexOf(key, StringComparison.OrdinalIgnoreCase) >= 0 && xml.IndexOf(NamespaceUri, StringComparison.OrdinalIgnoreCase) >= 0)
            {
                list.Add(part);
            }
        }
        return list;
    }

    private void DeleteByKey(string key)
    {
        var toDelete = GetPartsByKey(key).ToList();
        foreach (var p in toDelete)
        {
            try { p.Delete(); } catch { }
        }
    }

    private static string SlideKey(int slideId) => $"slide:{slideId}";

    private static IEnumerable<string> SplitChunks(string s, int chunkSize)
    {
        if (string.IsNullOrEmpty(s))
        {
            yield break;
        }
        for (var i = 0; i < s.Length; i += chunkSize)
        {
            yield return s.Substring(i, Math.Min(chunkSize, s.Length - i));
        }
    }

    private static int SafeInt(string? s)
    {
        if (int.TryParse(s ?? "", out var v))
        {
            return v;
        }
        return 0;
    }

    private static XDocument? SafeParse(string xml)
    {
        try
        {
            return XDocument.Parse(xml, LoadOptions.None);
        }
        catch
        {
            return null;
        }
    }

    private static byte[] Gzip(byte[] data)
    {
        using var ms = new MemoryStream();
        using (var gz = new GZipStream(ms, CompressionLevel.Optimal, leaveOpen: true))
        {
            gz.Write(data, 0, data.Length);
        }
        return ms.ToArray();
    }

    private static byte[] Gunzip(byte[] data)
    {
        using var input = new MemoryStream(data);
        using var gz = new GZipStream(input, CompressionMode.Decompress);
        using var output = new MemoryStream();
        gz.CopyTo(output);
        return output.ToArray();
    }

    private static string HashText(string value)
    {
        var t = value ?? "";
        unchecked
        {
            var hash = 23;
            for (var i = 0; i < t.Length; i++)
            {
                hash = (hash * 31) + t[i];
            }
            return Math.Abs(hash).ToString();
        }
    }
}

