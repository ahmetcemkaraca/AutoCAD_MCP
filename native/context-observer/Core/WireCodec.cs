using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Text;
using System.Text.RegularExpressions;
using System.Xml;

namespace AutoCadMcp.ContextObserver
{
    public sealed class StateRequest
    {
        public string Nonce { get; }
        public uint ClientPid { get; }
        public ulong DocumentHwnd { get; }
        public StateRequest(string nonce, uint clientPid, ulong documentHwnd)
        {
            WireCodec.Nonce(nonce); if (clientPid == 0 || documentHwnd == 0) throw new NativeProtocolException();
            Nonce = nonce; ClientPid = clientPid; DocumentHwnd = documentHwnd;
        }
    }
    public static class WireCodec
    {
        public const int MaxRequestBytes = 4096;
        public const int MaxResponseBytes = 8192;
        private static readonly UTF8Encoding Utf8 = new UTF8Encoding(false, true);
        private static readonly HashSet<string> Errors = new HashSet<string>(StringComparer.Ordinal)
            {"UNAVAILABLE","BUSY","INVALID_REQUEST","TIMEOUT","UNTRUSTED_PEER"};
        private sealed class Number { internal readonly string Text; internal Number(string text) { Text = text; } }
        private static void Require(bool value) { if (!value) throw new NativeProtocolException(); }
        internal static string Nonce(object? value)
        { Require(value is string && Regex.IsMatch((string)value, "\\A[0-9a-f]{64}\\z")); return (string)value!; }
        private static Guid Uuid(object? value)
        {
            Guid guid;
            Require(value is string && Guid.TryParseExact((string)value, "D", out guid));
            guid = Guid.ParseExact((string)value!, "D");
            Require(guid.ToString("D") == (string)value!); return guid;
        }
        public static byte[] Frame(byte[] payload, int limit)
        {
            Require((limit == MaxRequestBytes || limit == MaxResponseBytes) && payload.Length > 0 && payload.Length <= limit);
            var frame = new byte[payload.Length + 4]; var length = (uint)payload.Length;
            for (int i = 0; i < 4; i++) frame[i] = (byte)(length >> (8 * i));
            Buffer.BlockCopy(payload, 0, frame, 4, payload.Length); return frame;
        }
        private static uint Length(byte[] header)
        { return (uint)header[0] | ((uint)header[1] << 8) | ((uint)header[2] << 16) | ((uint)header[3] << 24); }
        private static byte[] Exact(Stream stream, int length)
        {
            var result = new byte[length]; int offset = 0;
            while (offset < length) { int count = stream.Read(result, offset, length - offset); Require(count > 0); offset += count; }
            return result;
        }
        public static byte[] ReadFrame(Stream stream, int limit)
        {
            Require(limit == MaxRequestBytes || limit == MaxResponseBytes);
            var header = Exact(stream, 4); var length = Length(header);
            Require(length > 0 && length <= limit);
            return Frame(Exact(stream, (int)length), limit);
        }
        private static string PropertyName(XmlDictionaryReader reader)
        {
            bool mapped = reader.LocalName == "item" && reader.NamespaceURI == "item";
            Require(reader.NamespaceURI == "" || mapped);
            return mapped ? reader.GetAttribute("item")! : reader.LocalName;
        }
        private static void Attributes(XmlDictionaryReader reader)
        {
            bool mapped = reader.LocalName == "item" && reader.NamespaceURI == "item";
            string prefix = reader.Prefix;
            if (reader.MoveToFirstAttribute())
            {
                do
                {
                    bool allowed = reader.NamespaceURI == "" && (reader.LocalName == "type" ||
                        (mapped && reader.LocalName == "item"));
                    allowed |= mapped && reader.NamespaceURI == "http://www.w3.org/2000/xmlns/" &&
                        reader.LocalName == prefix && reader.Value == "item";
                    Require(allowed);
                } while (reader.MoveToNextAttribute());
                reader.MoveToElement();
            }
        }
        private static object? ReadValue(XmlDictionaryReader reader, int depth)
        {
            Require(depth <= 3 && reader.NodeType == XmlNodeType.Element);
            Attributes(reader);
            var type = reader.GetAttribute("type");
            if (type == "object")
            {
                var result = new Dictionary<string, object?>(StringComparer.Ordinal);
                bool empty = reader.IsEmptyElement; reader.ReadStartElement();
                if (!empty)
                {
                    while (reader.MoveToContent() != XmlNodeType.EndElement)
                    {
                        Require(reader.NodeType == XmlNodeType.Element);
                        string key = PropertyName(reader);
                        Require(!result.ContainsKey(key) && result.Count < 8);
                        result.Add(key, ReadValue(reader, depth + 1));
                    }
                    reader.ReadEndElement();
                }
                return result;
            }
            Require(type == "string" || type == "number" || type == "boolean" || type == "null");
            string text = reader.ReadElementContentAsString();
            Require(text.Length <= 128 && IsAscii(text));
            if (type == "number") return new Number(text);
            if (type == "null") { Require(text.Length == 0); return null; }
            if (type == "boolean") { Require(text == "true" || text == "false"); return text == "true"; }
            return text;
        }
        private static bool IsAscii(string value)
        { foreach (char c in value) if (c > 127 || char.IsControl(c)) return false; return true; }
        // The legacy BCL reader stops at its first root. Enforce the full payload boundary
        // and reject trailing commas without replacing the BCL syntax/type parser.
        private static void CompleteObject(string text)
        {
            bool quoted = false, escaped = false; int depth = 0; char previous = '\0'; bool ended = false;
            foreach (char c in text)
            {
                if (ended) { Require(c == ' ' || c == '\t' || c == '\r' || c == '\n'); continue; }
                if (quoted)
                {
                    if (escaped) escaped = false;
                    else if (c == '\\') escaped = true;
                    else if (c == '"') quoted = false;
                    continue;
                }
                if (c == ' ' || c == '\t' || c == '\r' || c == '\n') continue;
                if (depth == 0) Require(c == '{');
                if (c == '"') quoted = true;
                else if (c == '{' || c == '[') depth++;
                else if (c == '}' || c == ']') { Require(previous != ','); depth--; if (depth == 0) ended = true; }
                previous = c;
            }
            Require(ended && !quoted && depth == 0);
        }
        private static Dictionary<string, object?> Payload(byte[] frame, int limit)
        {
            try
            {
                Require(frame.Length >= 4); var length = Length(frame);
                Require(length > 0 && length <= limit && frame.Length == length + 4);
                CompleteObject(Utf8.GetString(frame, 4, (int)length));
                var quotas = new XmlDictionaryReaderQuotas
                {
                    MaxDepth = 8,
                    MaxStringContentLength = 1024,
                    MaxArrayLength = 16,
                    MaxBytesPerRead = 8192,
                    MaxNameTableCharCount = 1024
                };
                using (var reader = JsonReaderWriterFactory.CreateJsonReader(frame, 4, (int)length, quotas))
                {
                    reader.MoveToContent(); Require(reader.LocalName == "root");
                    var value = ReadValue(reader, 0); Require(value is Dictionary<string, object?>);
                    Require(reader.MoveToContent() == XmlNodeType.None);
                    return (Dictionary<string, object?>)value!;
                }
            }
            catch (NativeProtocolException) { throw; }
            catch (Exception ex) when (ex is XmlException || ex is SerializationException ||
                                     ex is DecoderFallbackException || ex is FormatException || ex is ArgumentException)
            { throw new NativeProtocolException(); }
        }
        private static void Fields(Dictionary<string, object?> value, params string[] fields)
        { Require(value.Count == fields.Length); foreach (var field in fields) Require(value.ContainsKey(field)); }
        private static void Version(object? value) { Require(value is Number && ((Number)value).Text == "1"); }
        public static StateRequest DecodeRequest(byte[] frame)
        {
            var value = Payload(frame, MaxRequestBytes);
            Fields(value, "version", "operation", "nonce", "client_pid", "document_hwnd");
            Version(value["version"]); Require(value["operation"] is string && (string)value["operation"]! == "read_state");
            Require(value["client_pid"] is Number); string pidText = ((Number)value["client_pid"]!).Text;
            uint pid; Require(Regex.IsMatch(pidText, "\\A[1-9][0-9]{0,9}\\z") && uint.TryParse(pidText, NumberStyles.None, CultureInfo.InvariantCulture, out pid));
            pid = uint.Parse(pidText, CultureInfo.InvariantCulture);
            Require(value["document_hwnd"] is string && Regex.IsMatch((string)value["document_hwnd"]!, "\\A[0-9a-f]{16}\\z"));
            var hwnd = ulong.Parse((string)value["document_hwnd"]!, NumberStyles.HexNumber, CultureInfo.InvariantCulture);
            return new StateRequest(Nonce(value["nonce"]), pid, hwnd);
        }
        public static byte[] EncodeRequest(StateRequest request)
        {
            return Frame(Utf8.GetBytes("{\"version\":1,\"operation\":\"read_state\",\"nonce\":\"" + request.Nonce +
                "\",\"client_pid\":" + request.ClientPid.ToString(CultureInfo.InvariantCulture) + ",\"document_hwnd\":\"" +
                request.DocumentHwnd.ToString("x16", CultureInfo.InvariantCulture) + "\"}"), MaxRequestBytes);
        }
        public static byte[] EncodeResponse(string nonce, RevisionWitness witness)
        {
            Nonce(nonce);
            string guid = witness.DatabaseGuid.HasValue ? "\"" + witness.DatabaseGuid.Value.ToString("D") + "\"" : "null";
            return Frame(Utf8.GetBytes("{\"version\":1,\"nonce\":\"" + nonce + "\",\"state\":{\"bridge_id\":\"" +
                witness.BridgeId.ToString("D") + "\",\"session_id\":\"" + witness.SessionId.ToString("D") +
                "\",\"epoch\":\"" + witness.Epoch.ToString(CultureInfo.InvariantCulture) + "\",\"database_guid\":" + guid +
                ",\"ready\":true,\"coverage\":\"context-facts-v1\"}}"), MaxResponseBytes);
        }
        public static byte[] EncodeError(string nonce, string code)
        { Nonce(nonce); Require(Errors.Contains(code)); return Frame(Utf8.GetBytes("{\"version\":1,\"nonce\":\"" + nonce + "\",\"error\":\"" + code + "\"}"), MaxResponseBytes); }
        public static RevisionWitness DecodeResponse(byte[] frame, string expectedNonce)
        {
            Nonce(expectedNonce); var value = Payload(frame, MaxResponseBytes);
            if (value.ContainsKey("error")) Fields(value, "version", "nonce", "error");
            else Fields(value, "version", "nonce", "state");
            Version(value["version"]); Nonce(value["nonce"]);
            if ((string)value["nonce"]! != expectedNonce) throw new NativeProtocolException("UNTRUSTED_PEER");
            if (value.ContainsKey("error")) { Require(value["error"] is string && Errors.Contains((string)value["error"]!)); throw new NativeProtocolException((string)value["error"]!); }
            Require(value["state"] is Dictionary<string, object?>); var state = (Dictionary<string, object?>)value["state"]!;
            Fields(state, "bridge_id", "session_id", "epoch", "database_guid", "ready", "coverage");
            Require(state["ready"] is bool && (bool)state["ready"]! && state["coverage"] is string && (string)state["coverage"]! == "context-facts-v1");
            Require(state["epoch"] is string); string epochText = (string)state["epoch"]!; ulong epoch;
            Require(Regex.IsMatch(epochText, "\\A[1-9][0-9]{0,19}\\z") && ulong.TryParse(epochText, NumberStyles.None, CultureInfo.InvariantCulture, out epoch));
            epoch = ulong.Parse(epochText, CultureInfo.InvariantCulture);
            return new RevisionWitness(Uuid(state["bridge_id"]), Uuid(state["session_id"]), epoch,
                state["database_guid"] == null ? (Guid?)null : Uuid(state["database_guid"]));
        }
    }
}
