/* Generated from studio.schema.json. CSP-safe static validators; do not edit. */
var __getOwnPropNames = Object.getOwnPropertyNames;
var __commonJS = (cb, mod) => function __require() {
  return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
};

// node_modules/ajv/dist/runtime/ucs2length.js
var require_ucs2length = __commonJS({
  "node_modules/ajv/dist/runtime/ucs2length.js"(exports) {
    "use strict";
    Object.defineProperty(exports, "__esModule", { value: true });
    function ucs2length(str) {
      const len = str.length;
      let length = 0;
      let pos = 0;
      let value;
      while (pos < len) {
        length++;
        value = str.charCodeAt(pos++);
        if (value >= 55296 && value <= 56319 && pos < len) {
          value = str.charCodeAt(pos);
          if ((value & 64512) === 56320)
            pos++;
        }
      }
      return length;
    }
    exports.default = ucs2length;
    ucs2length.code = 'require("ajv/dist/runtime/ucs2length").default';
  }
});

// node_modules/ajv-formats/dist/formats.js
var require_formats = __commonJS({
  "node_modules/ajv-formats/dist/formats.js"(exports) {
    "use strict";
    Object.defineProperty(exports, "__esModule", { value: true });
    exports.formatNames = exports.fastFormats = exports.fullFormats = void 0;
    function fmtDef(validate, compare) {
      return { validate, compare };
    }
    exports.fullFormats = {
      // date: http://tools.ietf.org/html/rfc3339#section-5.6
      date: fmtDef(date, compareDate),
      // date-time: http://tools.ietf.org/html/rfc3339#section-5.6
      time: fmtDef(getTime(true), compareTime),
      "date-time": fmtDef(getDateTime(true), compareDateTime),
      "iso-time": fmtDef(getTime(), compareIsoTime),
      "iso-date-time": fmtDef(getDateTime(), compareIsoDateTime),
      // duration: https://tools.ietf.org/html/rfc3339#appendix-A
      duration: /^P(?!$)((\d+Y)?(\d+M)?(\d+D)?(T(?=\d)(\d+H)?(\d+M)?(\d+S)?)?|(\d+W)?)$/,
      uri,
      "uri-reference": /^(?:[a-z][a-z0-9+\-.]*:)?(?:\/?\/(?:(?:[a-z0-9\-._~!$&'()*+,;=:]|%[0-9a-f]{2})*@)?(?:\[(?:(?:(?:(?:[0-9a-f]{1,4}:){6}|::(?:[0-9a-f]{1,4}:){5}|(?:[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){4}|(?:(?:[0-9a-f]{1,4}:){0,1}[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){3}|(?:(?:[0-9a-f]{1,4}:){0,2}[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){2}|(?:(?:[0-9a-f]{1,4}:){0,3}[0-9a-f]{1,4})?::[0-9a-f]{1,4}:|(?:(?:[0-9a-f]{1,4}:){0,4}[0-9a-f]{1,4})?::)(?:[0-9a-f]{1,4}:[0-9a-f]{1,4}|(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?))|(?:(?:[0-9a-f]{1,4}:){0,5}[0-9a-f]{1,4})?::[0-9a-f]{1,4}|(?:(?:[0-9a-f]{1,4}:){0,6}[0-9a-f]{1,4})?::)|[Vv][0-9a-f]+\.[a-z0-9\-._~!$&'()*+,;=:]+)\]|(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)|(?:[a-z0-9\-._~!$&'"()*+,;=]|%[0-9a-f]{2})*)(?::\d*)?(?:\/(?:[a-z0-9\-._~!$&'"()*+,;=:@]|%[0-9a-f]{2})*)*|\/(?:(?:[a-z0-9\-._~!$&'"()*+,;=:@]|%[0-9a-f]{2})+(?:\/(?:[a-z0-9\-._~!$&'"()*+,;=:@]|%[0-9a-f]{2})*)*)?|(?:[a-z0-9\-._~!$&'"()*+,;=:@]|%[0-9a-f]{2})+(?:\/(?:[a-z0-9\-._~!$&'"()*+,;=:@]|%[0-9a-f]{2})*)*)?(?:\?(?:[a-z0-9\-._~!$&'"()*+,;=:@/?]|%[0-9a-f]{2})*)?(?:#(?:[a-z0-9\-._~!$&'"()*+,;=:@/?]|%[0-9a-f]{2})*)?$/i,
      // uri-template: https://tools.ietf.org/html/rfc6570
      "uri-template": /^(?:(?:[^\x00-\x20"'<>%\\^`{|}]|%[0-9a-f]{2})|\{[+#./;?&=,!@|]?(?:[a-z0-9_]|%[0-9a-f]{2})+(?::[1-9][0-9]{0,3}|\*)?(?:,(?:[a-z0-9_]|%[0-9a-f]{2})+(?::[1-9][0-9]{0,3}|\*)?)*\})*$/i,
      // For the source: https://gist.github.com/dperini/729294
      // For test cases: https://mathiasbynens.be/demo/url-regex
      url: /^(?:https?|ftp):\/\/(?:\S+(?::\S*)?@)?(?:(?!(?:10|127)(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z0-9\u{00a1}-\u{ffff}]+-)*[a-z0-9\u{00a1}-\u{ffff}]+)(?:\.(?:[a-z0-9\u{00a1}-\u{ffff}]+-)*[a-z0-9\u{00a1}-\u{ffff}]+)*(?:\.(?:[a-z\u{00a1}-\u{ffff}]{2,})))(?::\d{2,5})?(?:\/[^\s]*)?$/iu,
      email: /^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/i,
      hostname: /^(?=.{1,253}\.?$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[-0-9a-z]{0,61}[0-9a-z])?)*\.?$/i,
      // optimized https://www.safaribooksonline.com/library/view/regular-expressions-cookbook/9780596802837/ch07s16.html
      ipv4: /^(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$/,
      ipv6: /^((([0-9a-f]{1,4}:){7}([0-9a-f]{1,4}|:))|(([0-9a-f]{1,4}:){6}(:[0-9a-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9a-f]{1,4}:){5}(((:[0-9a-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9a-f]{1,4}:){4}(((:[0-9a-f]{1,4}){1,3})|((:[0-9a-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9a-f]{1,4}:){3}(((:[0-9a-f]{1,4}){1,4})|((:[0-9a-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9a-f]{1,4}:){2}(((:[0-9a-f]{1,4}){1,5})|((:[0-9a-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9a-f]{1,4}:){1}(((:[0-9a-f]{1,4}){1,6})|((:[0-9a-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9a-f]{1,4}){1,7})|((:[0-9a-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))$/i,
      regex,
      // uuid: http://tools.ietf.org/html/rfc4122
      uuid: /^(?:urn:uuid:)?[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i,
      // JSON-pointer: https://tools.ietf.org/html/rfc6901
      // uri fragment: https://tools.ietf.org/html/rfc3986#appendix-A
      "json-pointer": /^(?:\/(?:[^~/]|~0|~1)*)*$/,
      "json-pointer-uri-fragment": /^#(?:\/(?:[a-z0-9_\-.!$&'()*+,;:=@]|%[0-9a-f]{2}|~0|~1)*)*$/i,
      // relative JSON-pointer: http://tools.ietf.org/html/draft-luff-relative-json-pointer-00
      "relative-json-pointer": /^(?:0|[1-9][0-9]*)(?:#|(?:\/(?:[^~/]|~0|~1)*)*)$/,
      // the following formats are used by the openapi specification: https://spec.openapis.org/oas/v3.0.0#data-types
      // byte: https://github.com/miguelmota/is-base64
      byte,
      // signed 32 bit integer
      int32: { type: "number", validate: validateInt32 },
      // signed 64 bit integer
      int64: { type: "number", validate: validateInt64 },
      // C-type float
      float: { type: "number", validate: validateNumber },
      // C-type double
      double: { type: "number", validate: validateNumber },
      // hint to the UI to hide input strings
      password: true,
      // unchecked string payload
      binary: true
    };
    exports.fastFormats = {
      ...exports.fullFormats,
      date: fmtDef(/^\d\d\d\d-[0-1]\d-[0-3]\d$/, compareDate),
      time: fmtDef(/^(?:[0-2]\d:[0-5]\d:[0-5]\d|23:59:60)(?:\.\d+)?(?:z|[+-]\d\d(?::?\d\d)?)$/i, compareTime),
      "date-time": fmtDef(/^\d\d\d\d-[0-1]\d-[0-3]\dt(?:[0-2]\d:[0-5]\d:[0-5]\d|23:59:60)(?:\.\d+)?(?:z|[+-]\d\d(?::?\d\d)?)$/i, compareDateTime),
      "iso-time": fmtDef(/^(?:[0-2]\d:[0-5]\d:[0-5]\d|23:59:60)(?:\.\d+)?(?:z|[+-]\d\d(?::?\d\d)?)?$/i, compareIsoTime),
      "iso-date-time": fmtDef(/^\d\d\d\d-[0-1]\d-[0-3]\d[t\s](?:[0-2]\d:[0-5]\d:[0-5]\d|23:59:60)(?:\.\d+)?(?:z|[+-]\d\d(?::?\d\d)?)?$/i, compareIsoDateTime),
      // uri: https://github.com/mafintosh/is-my-json-valid/blob/master/formats.js
      uri: /^(?:[a-z][a-z0-9+\-.]*:)(?:\/?\/)?[^\s]*$/i,
      "uri-reference": /^(?:(?:[a-z][a-z0-9+\-.]*:)?\/?\/)?(?:[^\\\s#][^\s#]*)?(?:#[^\\\s]*)?$/i,
      // email (sources from jsen validator):
      // http://stackoverflow.com/questions/201323/using-a-regular-expression-to-validate-an-email-address#answer-8829363
      // http://www.w3.org/TR/html5/forms.html#valid-e-mail-address (search for 'wilful violation')
      email: /^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$/i
    };
    exports.formatNames = Object.keys(exports.fullFormats);
    function isLeapYear(year) {
      return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    }
    var DATE = /^(\d\d\d\d)-(\d\d)-(\d\d)$/;
    var DAYS = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    function date(str) {
      const matches = DATE.exec(str);
      if (!matches)
        return false;
      const year = +matches[1];
      const month = +matches[2];
      const day = +matches[3];
      return month >= 1 && month <= 12 && day >= 1 && day <= (month === 2 && isLeapYear(year) ? 29 : DAYS[month]);
    }
    function compareDate(d1, d2) {
      if (!(d1 && d2))
        return void 0;
      if (d1 > d2)
        return 1;
      if (d1 < d2)
        return -1;
      return 0;
    }
    var TIME = /^(\d\d):(\d\d):(\d\d(?:\.\d+)?)(z|([+-])(\d\d)(?::?(\d\d))?)?$/i;
    function getTime(strictTimeZone) {
      return function time(str) {
        const matches = TIME.exec(str);
        if (!matches)
          return false;
        const hr = +matches[1];
        const min = +matches[2];
        const sec = +matches[3];
        const tz = matches[4];
        const tzSign = matches[5] === "-" ? -1 : 1;
        const tzH = +(matches[6] || 0);
        const tzM = +(matches[7] || 0);
        if (tzH > 23 || tzM > 59 || strictTimeZone && !tz)
          return false;
        if (hr <= 23 && min <= 59 && sec < 60)
          return true;
        const utcMin = min - tzM * tzSign;
        const utcHr = hr - tzH * tzSign - (utcMin < 0 ? 1 : 0);
        return (utcHr === 23 || utcHr === -1) && (utcMin === 59 || utcMin === -1) && sec < 61;
      };
    }
    function compareTime(s1, s2) {
      if (!(s1 && s2))
        return void 0;
      const t1 = (/* @__PURE__ */ new Date("2020-01-01T" + s1)).valueOf();
      const t2 = (/* @__PURE__ */ new Date("2020-01-01T" + s2)).valueOf();
      if (!(t1 && t2))
        return void 0;
      return t1 - t2;
    }
    function compareIsoTime(t1, t2) {
      if (!(t1 && t2))
        return void 0;
      const a1 = TIME.exec(t1);
      const a2 = TIME.exec(t2);
      if (!(a1 && a2))
        return void 0;
      t1 = a1[1] + a1[2] + a1[3];
      t2 = a2[1] + a2[2] + a2[3];
      if (t1 > t2)
        return 1;
      if (t1 < t2)
        return -1;
      return 0;
    }
    var DATE_TIME_SEPARATOR = /t|\s/i;
    function getDateTime(strictTimeZone) {
      const time = getTime(strictTimeZone);
      return function date_time(str) {
        const dateTime = str.split(DATE_TIME_SEPARATOR);
        return dateTime.length === 2 && date(dateTime[0]) && time(dateTime[1]);
      };
    }
    function compareDateTime(dt1, dt2) {
      if (!(dt1 && dt2))
        return void 0;
      const d1 = new Date(dt1).valueOf();
      const d2 = new Date(dt2).valueOf();
      if (!(d1 && d2))
        return void 0;
      return d1 - d2;
    }
    function compareIsoDateTime(dt1, dt2) {
      if (!(dt1 && dt2))
        return void 0;
      const [d1, t1] = dt1.split(DATE_TIME_SEPARATOR);
      const [d2, t2] = dt2.split(DATE_TIME_SEPARATOR);
      const res = compareDate(d1, d2);
      if (res === void 0)
        return void 0;
      return res || compareTime(t1, t2);
    }
    var NOT_URI_FRAGMENT = /\/|:/;
    var URI = /^(?:[a-z][a-z0-9+\-.]*:)(?:\/?\/(?:(?:[a-z0-9\-._~!$&'()*+,;=:]|%[0-9a-f]{2})*@)?(?:\[(?:(?:(?:(?:[0-9a-f]{1,4}:){6}|::(?:[0-9a-f]{1,4}:){5}|(?:[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){4}|(?:(?:[0-9a-f]{1,4}:){0,1}[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){3}|(?:(?:[0-9a-f]{1,4}:){0,2}[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){2}|(?:(?:[0-9a-f]{1,4}:){0,3}[0-9a-f]{1,4})?::[0-9a-f]{1,4}:|(?:(?:[0-9a-f]{1,4}:){0,4}[0-9a-f]{1,4})?::)(?:[0-9a-f]{1,4}:[0-9a-f]{1,4}|(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?))|(?:(?:[0-9a-f]{1,4}:){0,5}[0-9a-f]{1,4})?::[0-9a-f]{1,4}|(?:(?:[0-9a-f]{1,4}:){0,6}[0-9a-f]{1,4})?::)|[Vv][0-9a-f]+\.[a-z0-9\-._~!$&'()*+,;=:]+)\]|(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)|(?:[a-z0-9\-._~!$&'()*+,;=]|%[0-9a-f]{2})*)(?::\d*)?(?:\/(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})*)*|\/(?:(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})+(?:\/(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})*)*)?|(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})+(?:\/(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})*)*)(?:\?(?:[a-z0-9\-._~!$&'()*+,;=:@/?]|%[0-9a-f]{2})*)?(?:#(?:[a-z0-9\-._~!$&'()*+,;=:@/?]|%[0-9a-f]{2})*)?$/i;
    function uri(str) {
      return NOT_URI_FRAGMENT.test(str) && URI.test(str);
    }
    var BYTE = /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/gm;
    function byte(str) {
      BYTE.lastIndex = 0;
      return BYTE.test(str);
    }
    var MIN_INT32 = -(2 ** 31);
    var MAX_INT32 = 2 ** 31 - 1;
    function validateInt32(value) {
      return Number.isInteger(value) && value <= MAX_INT32 && value >= MIN_INT32;
    }
    function validateInt64(value) {
      return Number.isInteger(value);
    }
    function validateNumber() {
      return true;
    }
    var Z_ANCHOR = /[^\\]\\Z/;
    function regex(str) {
      if (Z_ANCHOR.test(str))
        return false;
      try {
        new RegExp(str);
        return true;
      } catch (e) {
        return false;
      }
    }
  }
});

// studio-validators.js
var jobShape = validate10;
var schema25 = { "type": "object", "additionalProperties": false, "properties": { "jobId": { "type": "string" }, "status": { "type": "string", "enum": ["queued", "running", "succeeded", "failed"] }, "events": { "type": "array", "items": { "$ref": "#/definitions/StudioEvent" } }, "result": { "anyOf": [{ "$ref": "#/definitions/StudioResult" }, { "type": "null" }] }, "error": { "anyOf": [{ "$ref": "#/definitions/StudioError" }, { "type": "null" }] }, "changeApproval": { "$ref": "#/definitions/ChangeApproval" } }, "required": ["jobId", "status", "events", "result", "error"] };
var schema26 = { "type": "object", "additionalProperties": false, "properties": { "sequence": { "type": "integer", "minimum": 1 }, "stage": { "type": "string", "enum": ["intake", "synthesis", "assurance", "complete", "error"] }, "message": { "type": "string" }, "at": { "type": "string" } }, "required": ["sequence", "stage", "message", "at"] };
var schema28 = { "type": "object", "additionalProperties": false, "properties": { "role": { "type": "string", "enum": ["synthesis", "assurance"] }, "model": { "type": "string" }, "responseId": { "type": "string", "minLength": 1 }, "durationMs": { "type": "integer", "minimum": 0 } }, "required": ["role", "model", "responseId", "durationMs"] };
var schema17 = { "type": "object", "additionalProperties": false, "properties": { "title": { "type": "string", "minLength": 1, "maxLength": 160 }, "summary": { "type": "string", "minLength": 1, "maxLength": 1800 }, "businessProcess": { "type": "array", "minItems": 2, "maxItems": 10, "items": { "type": "string", "maxLength": 400 } }, "requirements": { "type": "array", "minItems": 2, "maxItems": 16, "items": { "$ref": "#/definitions/Requirement" } }, "assumptions": { "type": "array", "maxItems": 10, "items": { "type": "string", "maxLength": 600 } }, "questions": { "type": "array", "maxItems": 6, "items": { "$ref": "#/definitions/Question" } }, "options": { "type": "array", "minItems": 2, "maxItems": 3, "items": { "$ref": "#/definitions/ArchitectureOption" } }, "recommendedOptionId": { "type": "string", "maxLength": 40 }, "review": { "type": "array", "minItems": 9, "maxItems": 9, "items": { "$ref": "#/definitions/ReviewFinding" } }, "changeSummary": { "type": "string", "minLength": 1, "maxLength": 1e3 } }, "required": ["title", "summary", "businessProcess", "requirements", "assumptions", "questions", "options", "recommendedOptionId", "review", "changeSummary"] };
var schema16 = { "type": "object", "additionalProperties": false, "properties": { "dimension": { "type": "string", "enum": ["business", "security", "reliability", "performance", "cost", "integration", "compliance", "operations", "delivery"] }, "severity": { "type": "string", "enum": ["info", "warning", "blocker"] }, "finding": { "type": "string", "minLength": 1, "maxLength": 1e3 }, "recommendation": { "type": "string", "minLength": 1, "maxLength": 1e3 }, "sourceIds": { "type": "array", "minItems": 1, "maxItems": 6, "uniqueItems": true, "items": { "type": "string", "maxLength": 128 } } }, "required": ["dimension", "severity", "finding", "recommendation", "sourceIds"] };
var func24 = Object.prototype.hasOwnProperty;
var func2 = require_ucs2length().default;
var pattern0 = new RegExp("^[a-z][a-z0-9-]{0,39}$", "u");
var schema21 = { "type": "object", "additionalProperties": false, "properties": { "id": { "type": "string", "pattern": "^[a-z][a-z0-9-]{0,39}$" }, "label": { "type": "string", "minLength": 1, "maxLength": 100 }, "kind": { "type": "string", "enum": ["appservice", "functions", "storage", "servicebus", "keyvault", "external", "client"] }, "service": { "type": "string", "minLength": 1, "maxLength": 160 }, "responsibility": { "type": "string", "minLength": 1, "maxLength": 600 }, "requirementIds": { "type": "array", "minItems": 1, "maxItems": 20, "uniqueItems": true, "items": { "type": "string", "maxLength": 64 } }, "externalDependency": { "anyOf": [{ "$ref": "#/definitions/ExternalDependency" }, { "type": "null" }] } }, "required": ["id", "label", "kind", "service", "responsibility", "requirementIds"] };
function validate18(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.id === void 0) {
      const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.label === void 0) {
      const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "label" }, message: "must have required property 'label'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    if (data.kind === void 0) {
      const err2 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "kind" }, message: "must have required property 'kind'" };
      if (vErrors === null) {
        vErrors = [err2];
      } else {
        vErrors.push(err2);
      }
      errors++;
    }
    if (data.service === void 0) {
      const err3 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "service" }, message: "must have required property 'service'" };
      if (vErrors === null) {
        vErrors = [err3];
      } else {
        vErrors.push(err3);
      }
      errors++;
    }
    if (data.responsibility === void 0) {
      const err4 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "responsibility" }, message: "must have required property 'responsibility'" };
      if (vErrors === null) {
        vErrors = [err4];
      } else {
        vErrors.push(err4);
      }
      errors++;
    }
    if (data.requirementIds === void 0) {
      const err5 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "requirementIds" }, message: "must have required property 'requirementIds'" };
      if (vErrors === null) {
        vErrors = [err5];
      } else {
        vErrors.push(err5);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!(key0 === "id" || key0 === "label" || key0 === "kind" || key0 === "service" || key0 === "responsibility" || key0 === "requirementIds" || key0 === "externalDependency")) {
        const err6 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err6];
        } else {
          vErrors.push(err6);
        }
        errors++;
      }
    }
    if (data.id !== void 0) {
      let data0 = data.id;
      if (typeof data0 === "string") {
        if (!pattern0.test(data0)) {
          const err7 = { instancePath: instancePath + "/id", schemaPath: "#/properties/id/pattern", keyword: "pattern", params: { pattern: "^[a-z][a-z0-9-]{0,39}$" }, message: 'must match pattern "^[a-z][a-z0-9-]{0,39}$"' };
          if (vErrors === null) {
            vErrors = [err7];
          } else {
            vErrors.push(err7);
          }
          errors++;
        }
      } else {
        const err8 = { instancePath: instancePath + "/id", schemaPath: "#/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err8];
        } else {
          vErrors.push(err8);
        }
        errors++;
      }
    }
    if (data.label !== void 0) {
      let data1 = data.label;
      if (typeof data1 === "string") {
        if (func2(data1) > 100) {
          const err9 = { instancePath: instancePath + "/label", schemaPath: "#/properties/label/maxLength", keyword: "maxLength", params: { limit: 100 }, message: "must NOT have more than 100 characters" };
          if (vErrors === null) {
            vErrors = [err9];
          } else {
            vErrors.push(err9);
          }
          errors++;
        }
        if (func2(data1) < 1) {
          const err10 = { instancePath: instancePath + "/label", schemaPath: "#/properties/label/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
          if (vErrors === null) {
            vErrors = [err10];
          } else {
            vErrors.push(err10);
          }
          errors++;
        }
      } else {
        const err11 = { instancePath: instancePath + "/label", schemaPath: "#/properties/label/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err11];
        } else {
          vErrors.push(err11);
        }
        errors++;
      }
    }
    if (data.kind !== void 0) {
      let data2 = data.kind;
      if (typeof data2 !== "string") {
        const err12 = { instancePath: instancePath + "/kind", schemaPath: "#/properties/kind/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err12];
        } else {
          vErrors.push(err12);
        }
        errors++;
      }
      if (!(data2 === "appservice" || data2 === "functions" || data2 === "storage" || data2 === "servicebus" || data2 === "keyvault" || data2 === "external" || data2 === "client")) {
        const err13 = { instancePath: instancePath + "/kind", schemaPath: "#/properties/kind/enum", keyword: "enum", params: { allowedValues: schema21.properties.kind.enum }, message: "must be equal to one of the allowed values" };
        if (vErrors === null) {
          vErrors = [err13];
        } else {
          vErrors.push(err13);
        }
        errors++;
      }
    }
    if (data.service !== void 0) {
      let data3 = data.service;
      if (typeof data3 === "string") {
        if (func2(data3) > 160) {
          const err14 = { instancePath: instancePath + "/service", schemaPath: "#/properties/service/maxLength", keyword: "maxLength", params: { limit: 160 }, message: "must NOT have more than 160 characters" };
          if (vErrors === null) {
            vErrors = [err14];
          } else {
            vErrors.push(err14);
          }
          errors++;
        }
        if (func2(data3) < 1) {
          const err15 = { instancePath: instancePath + "/service", schemaPath: "#/properties/service/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
          if (vErrors === null) {
            vErrors = [err15];
          } else {
            vErrors.push(err15);
          }
          errors++;
        }
      } else {
        const err16 = { instancePath: instancePath + "/service", schemaPath: "#/properties/service/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err16];
        } else {
          vErrors.push(err16);
        }
        errors++;
      }
    }
    if (data.responsibility !== void 0) {
      let data4 = data.responsibility;
      if (typeof data4 === "string") {
        if (func2(data4) > 600) {
          const err17 = { instancePath: instancePath + "/responsibility", schemaPath: "#/properties/responsibility/maxLength", keyword: "maxLength", params: { limit: 600 }, message: "must NOT have more than 600 characters" };
          if (vErrors === null) {
            vErrors = [err17];
          } else {
            vErrors.push(err17);
          }
          errors++;
        }
        if (func2(data4) < 1) {
          const err18 = { instancePath: instancePath + "/responsibility", schemaPath: "#/properties/responsibility/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
          if (vErrors === null) {
            vErrors = [err18];
          } else {
            vErrors.push(err18);
          }
          errors++;
        }
      } else {
        const err19 = { instancePath: instancePath + "/responsibility", schemaPath: "#/properties/responsibility/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err19];
        } else {
          vErrors.push(err19);
        }
        errors++;
      }
    }
    if (data.requirementIds !== void 0) {
      let data5 = data.requirementIds;
      if (Array.isArray(data5)) {
        if (data5.length > 20) {
          const err20 = { instancePath: instancePath + "/requirementIds", schemaPath: "#/properties/requirementIds/maxItems", keyword: "maxItems", params: { limit: 20 }, message: "must NOT have more than 20 items" };
          if (vErrors === null) {
            vErrors = [err20];
          } else {
            vErrors.push(err20);
          }
          errors++;
        }
        if (data5.length < 1) {
          const err21 = { instancePath: instancePath + "/requirementIds", schemaPath: "#/properties/requirementIds/minItems", keyword: "minItems", params: { limit: 1 }, message: "must NOT have fewer than 1 items" };
          if (vErrors === null) {
            vErrors = [err21];
          } else {
            vErrors.push(err21);
          }
          errors++;
        }
        const len0 = data5.length;
        for (let i0 = 0; i0 < len0; i0++) {
          let data6 = data5[i0];
          if (typeof data6 === "string") {
            if (func2(data6) > 64) {
              const err22 = { instancePath: instancePath + "/requirementIds/" + i0, schemaPath: "#/properties/requirementIds/items/maxLength", keyword: "maxLength", params: { limit: 64 }, message: "must NOT have more than 64 characters" };
              if (vErrors === null) {
                vErrors = [err22];
              } else {
                vErrors.push(err22);
              }
              errors++;
            }
          } else {
            const err23 = { instancePath: instancePath + "/requirementIds/" + i0, schemaPath: "#/properties/requirementIds/items/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err23];
            } else {
              vErrors.push(err23);
            }
            errors++;
          }
        }
        let i1 = data5.length;
        let j0;
        if (i1 > 1) {
          const indices0 = {};
          for (; i1--; ) {
            let item0 = data5[i1];
            if (typeof item0 !== "string") {
              continue;
            }
            if (typeof indices0[item0] == "number") {
              j0 = indices0[item0];
              const err24 = { instancePath: instancePath + "/requirementIds", schemaPath: "#/properties/requirementIds/uniqueItems", keyword: "uniqueItems", params: { i: i1, j: j0 }, message: "must NOT have duplicate items (items ## " + j0 + " and " + i1 + " are identical)" };
              if (vErrors === null) {
                vErrors = [err24];
              } else {
                vErrors.push(err24);
              }
              errors++;
              break;
            }
            indices0[item0] = i1;
          }
        }
      } else {
        const err25 = { instancePath: instancePath + "/requirementIds", schemaPath: "#/properties/requirementIds/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err25];
        } else {
          vErrors.push(err25);
        }
        errors++;
      }
    }
    if (data.externalDependency !== void 0) {
      let data7 = data.externalDependency;
      const _errs17 = errors;
      let valid4 = false;
      const _errs18 = errors;
      if (data7 && typeof data7 == "object" && !Array.isArray(data7)) {
        if (data7.name === void 0) {
          const err26 = { instancePath: instancePath + "/externalDependency", schemaPath: "#/definitions/ExternalDependency/required", keyword: "required", params: { missingProperty: "name" }, message: "must have required property 'name'" };
          if (vErrors === null) {
            vErrors = [err26];
          } else {
            vErrors.push(err26);
          }
          errors++;
        }
        if (data7.sourceId === void 0) {
          const err27 = { instancePath: instancePath + "/externalDependency", schemaPath: "#/definitions/ExternalDependency/required", keyword: "required", params: { missingProperty: "sourceId" }, message: "must have required property 'sourceId'" };
          if (vErrors === null) {
            vErrors = [err27];
          } else {
            vErrors.push(err27);
          }
          errors++;
        }
        if (data7.quote === void 0) {
          const err28 = { instancePath: instancePath + "/externalDependency", schemaPath: "#/definitions/ExternalDependency/required", keyword: "required", params: { missingProperty: "quote" }, message: "must have required property 'quote'" };
          if (vErrors === null) {
            vErrors = [err28];
          } else {
            vErrors.push(err28);
          }
          errors++;
        }
        for (const key1 in data7) {
          if (!(key1 === "name" || key1 === "sourceId" || key1 === "quote")) {
            const err29 = { instancePath: instancePath + "/externalDependency", schemaPath: "#/definitions/ExternalDependency/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key1 }, message: "must NOT have additional properties" };
            if (vErrors === null) {
              vErrors = [err29];
            } else {
              vErrors.push(err29);
            }
            errors++;
          }
        }
        if (data7.name !== void 0) {
          let data8 = data7.name;
          if (typeof data8 === "string") {
            if (func2(data8) > 120) {
              const err30 = { instancePath: instancePath + "/externalDependency/name", schemaPath: "#/definitions/ExternalDependency/properties/name/maxLength", keyword: "maxLength", params: { limit: 120 }, message: "must NOT have more than 120 characters" };
              if (vErrors === null) {
                vErrors = [err30];
              } else {
                vErrors.push(err30);
              }
              errors++;
            }
            if (func2(data8) < 1) {
              const err31 = { instancePath: instancePath + "/externalDependency/name", schemaPath: "#/definitions/ExternalDependency/properties/name/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
              if (vErrors === null) {
                vErrors = [err31];
              } else {
                vErrors.push(err31);
              }
              errors++;
            }
          } else {
            const err32 = { instancePath: instancePath + "/externalDependency/name", schemaPath: "#/definitions/ExternalDependency/properties/name/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err32];
            } else {
              vErrors.push(err32);
            }
            errors++;
          }
        }
        if (data7.sourceId !== void 0) {
          let data9 = data7.sourceId;
          if (typeof data9 === "string") {
            if (func2(data9) > 128) {
              const err33 = { instancePath: instancePath + "/externalDependency/sourceId", schemaPath: "#/definitions/ExternalDependency/properties/sourceId/maxLength", keyword: "maxLength", params: { limit: 128 }, message: "must NOT have more than 128 characters" };
              if (vErrors === null) {
                vErrors = [err33];
              } else {
                vErrors.push(err33);
              }
              errors++;
            }
            if (func2(data9) < 1) {
              const err34 = { instancePath: instancePath + "/externalDependency/sourceId", schemaPath: "#/definitions/ExternalDependency/properties/sourceId/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
              if (vErrors === null) {
                vErrors = [err34];
              } else {
                vErrors.push(err34);
              }
              errors++;
            }
          } else {
            const err35 = { instancePath: instancePath + "/externalDependency/sourceId", schemaPath: "#/definitions/ExternalDependency/properties/sourceId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err35];
            } else {
              vErrors.push(err35);
            }
            errors++;
          }
        }
        if (data7.quote !== void 0) {
          let data10 = data7.quote;
          if (typeof data10 === "string") {
            if (func2(data10) > 2e3) {
              const err36 = { instancePath: instancePath + "/externalDependency/quote", schemaPath: "#/definitions/ExternalDependency/properties/quote/maxLength", keyword: "maxLength", params: { limit: 2e3 }, message: "must NOT have more than 2000 characters" };
              if (vErrors === null) {
                vErrors = [err36];
              } else {
                vErrors.push(err36);
              }
              errors++;
            }
            if (func2(data10) < 10) {
              const err37 = { instancePath: instancePath + "/externalDependency/quote", schemaPath: "#/definitions/ExternalDependency/properties/quote/minLength", keyword: "minLength", params: { limit: 10 }, message: "must NOT have fewer than 10 characters" };
              if (vErrors === null) {
                vErrors = [err37];
              } else {
                vErrors.push(err37);
              }
              errors++;
            }
          } else {
            const err38 = { instancePath: instancePath + "/externalDependency/quote", schemaPath: "#/definitions/ExternalDependency/properties/quote/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err38];
            } else {
              vErrors.push(err38);
            }
            errors++;
          }
        }
      } else {
        const err39 = { instancePath: instancePath + "/externalDependency", schemaPath: "#/definitions/ExternalDependency/type", keyword: "type", params: { type: "object" }, message: "must be object" };
        if (vErrors === null) {
          vErrors = [err39];
        } else {
          vErrors.push(err39);
        }
        errors++;
      }
      var _valid0 = _errs18 === errors;
      valid4 = valid4 || _valid0;
      if (!valid4) {
        const _errs28 = errors;
        if (data7 !== null) {
          const err40 = { instancePath: instancePath + "/externalDependency", schemaPath: "#/properties/externalDependency/anyOf/1/type", keyword: "type", params: { type: "null" }, message: "must be null" };
          if (vErrors === null) {
            vErrors = [err40];
          } else {
            vErrors.push(err40);
          }
          errors++;
        }
        var _valid0 = _errs28 === errors;
        valid4 = valid4 || _valid0;
      }
      if (!valid4) {
        const err41 = { instancePath: instancePath + "/externalDependency", schemaPath: "#/properties/externalDependency/anyOf", keyword: "anyOf", params: {}, message: "must match a schema in anyOf" };
        if (vErrors === null) {
          vErrors = [err41];
        } else {
          vErrors.push(err41);
        }
        errors++;
      } else {
        errors = _errs17;
        if (vErrors !== null) {
          if (_errs17) {
            vErrors.length = _errs17;
          } else {
            vErrors = null;
          }
        }
      }
    }
  } else {
    const err42 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err42];
    } else {
      vErrors.push(err42);
    }
    errors++;
  }
  validate18.errors = vErrors;
  return errors === 0;
}
function validate17(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.id === void 0) {
      const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.name === void 0) {
      const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "name" }, message: "must have required property 'name'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    if (data.rationale === void 0) {
      const err2 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "rationale" }, message: "must have required property 'rationale'" };
      if (vErrors === null) {
        vErrors = [err2];
      } else {
        vErrors.push(err2);
      }
      errors++;
    }
    if (data.tradeoffs === void 0) {
      const err3 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "tradeoffs" }, message: "must have required property 'tradeoffs'" };
      if (vErrors === null) {
        vErrors = [err3];
      } else {
        vErrors.push(err3);
      }
      errors++;
    }
    if (data.costNotes === void 0) {
      const err4 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "costNotes" }, message: "must have required property 'costNotes'" };
      if (vErrors === null) {
        vErrors = [err4];
      } else {
        vErrors.push(err4);
      }
      errors++;
    }
    if (data.components === void 0) {
      const err5 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "components" }, message: "must have required property 'components'" };
      if (vErrors === null) {
        vErrors = [err5];
      } else {
        vErrors.push(err5);
      }
      errors++;
    }
    if (data.connections === void 0) {
      const err6 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "connections" }, message: "must have required property 'connections'" };
      if (vErrors === null) {
        vErrors = [err6];
      } else {
        vErrors.push(err6);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!(key0 === "id" || key0 === "name" || key0 === "rationale" || key0 === "tradeoffs" || key0 === "costNotes" || key0 === "components" || key0 === "connections")) {
        const err7 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err7];
        } else {
          vErrors.push(err7);
        }
        errors++;
      }
    }
    if (data.id !== void 0) {
      let data0 = data.id;
      if (typeof data0 === "string") {
        if (!pattern0.test(data0)) {
          const err8 = { instancePath: instancePath + "/id", schemaPath: "#/properties/id/pattern", keyword: "pattern", params: { pattern: "^[a-z][a-z0-9-]{0,39}$" }, message: 'must match pattern "^[a-z][a-z0-9-]{0,39}$"' };
          if (vErrors === null) {
            vErrors = [err8];
          } else {
            vErrors.push(err8);
          }
          errors++;
        }
      } else {
        const err9 = { instancePath: instancePath + "/id", schemaPath: "#/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err9];
        } else {
          vErrors.push(err9);
        }
        errors++;
      }
    }
    if (data.name !== void 0) {
      let data1 = data.name;
      if (typeof data1 === "string") {
        if (func2(data1) > 120) {
          const err10 = { instancePath: instancePath + "/name", schemaPath: "#/properties/name/maxLength", keyword: "maxLength", params: { limit: 120 }, message: "must NOT have more than 120 characters" };
          if (vErrors === null) {
            vErrors = [err10];
          } else {
            vErrors.push(err10);
          }
          errors++;
        }
        if (func2(data1) < 1) {
          const err11 = { instancePath: instancePath + "/name", schemaPath: "#/properties/name/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
          if (vErrors === null) {
            vErrors = [err11];
          } else {
            vErrors.push(err11);
          }
          errors++;
        }
      } else {
        const err12 = { instancePath: instancePath + "/name", schemaPath: "#/properties/name/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err12];
        } else {
          vErrors.push(err12);
        }
        errors++;
      }
    }
    if (data.rationale !== void 0) {
      let data2 = data.rationale;
      if (typeof data2 === "string") {
        if (func2(data2) > 1200) {
          const err13 = { instancePath: instancePath + "/rationale", schemaPath: "#/properties/rationale/maxLength", keyword: "maxLength", params: { limit: 1200 }, message: "must NOT have more than 1200 characters" };
          if (vErrors === null) {
            vErrors = [err13];
          } else {
            vErrors.push(err13);
          }
          errors++;
        }
        if (func2(data2) < 1) {
          const err14 = { instancePath: instancePath + "/rationale", schemaPath: "#/properties/rationale/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
          if (vErrors === null) {
            vErrors = [err14];
          } else {
            vErrors.push(err14);
          }
          errors++;
        }
      } else {
        const err15 = { instancePath: instancePath + "/rationale", schemaPath: "#/properties/rationale/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err15];
        } else {
          vErrors.push(err15);
        }
        errors++;
      }
    }
    if (data.tradeoffs !== void 0) {
      let data3 = data.tradeoffs;
      if (Array.isArray(data3)) {
        if (data3.length > 6) {
          const err16 = { instancePath: instancePath + "/tradeoffs", schemaPath: "#/properties/tradeoffs/maxItems", keyword: "maxItems", params: { limit: 6 }, message: "must NOT have more than 6 items" };
          if (vErrors === null) {
            vErrors = [err16];
          } else {
            vErrors.push(err16);
          }
          errors++;
        }
        if (data3.length < 1) {
          const err17 = { instancePath: instancePath + "/tradeoffs", schemaPath: "#/properties/tradeoffs/minItems", keyword: "minItems", params: { limit: 1 }, message: "must NOT have fewer than 1 items" };
          if (vErrors === null) {
            vErrors = [err17];
          } else {
            vErrors.push(err17);
          }
          errors++;
        }
        const len0 = data3.length;
        for (let i0 = 0; i0 < len0; i0++) {
          let data4 = data3[i0];
          if (typeof data4 === "string") {
            if (func2(data4) > 600) {
              const err18 = { instancePath: instancePath + "/tradeoffs/" + i0, schemaPath: "#/properties/tradeoffs/items/maxLength", keyword: "maxLength", params: { limit: 600 }, message: "must NOT have more than 600 characters" };
              if (vErrors === null) {
                vErrors = [err18];
              } else {
                vErrors.push(err18);
              }
              errors++;
            }
          } else {
            const err19 = { instancePath: instancePath + "/tradeoffs/" + i0, schemaPath: "#/properties/tradeoffs/items/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err19];
            } else {
              vErrors.push(err19);
            }
            errors++;
          }
        }
      } else {
        const err20 = { instancePath: instancePath + "/tradeoffs", schemaPath: "#/properties/tradeoffs/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err20];
        } else {
          vErrors.push(err20);
        }
        errors++;
      }
    }
    if (data.costNotes !== void 0) {
      let data5 = data.costNotes;
      if (typeof data5 === "string") {
        if (func2(data5) > 800) {
          const err21 = { instancePath: instancePath + "/costNotes", schemaPath: "#/properties/costNotes/maxLength", keyword: "maxLength", params: { limit: 800 }, message: "must NOT have more than 800 characters" };
          if (vErrors === null) {
            vErrors = [err21];
          } else {
            vErrors.push(err21);
          }
          errors++;
        }
        if (func2(data5) < 1) {
          const err22 = { instancePath: instancePath + "/costNotes", schemaPath: "#/properties/costNotes/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
          if (vErrors === null) {
            vErrors = [err22];
          } else {
            vErrors.push(err22);
          }
          errors++;
        }
      } else {
        const err23 = { instancePath: instancePath + "/costNotes", schemaPath: "#/properties/costNotes/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err23];
        } else {
          vErrors.push(err23);
        }
        errors++;
      }
    }
    if (data.components !== void 0) {
      let data6 = data.components;
      if (Array.isArray(data6)) {
        if (data6.length > 12) {
          const err24 = { instancePath: instancePath + "/components", schemaPath: "#/properties/components/maxItems", keyword: "maxItems", params: { limit: 12 }, message: "must NOT have more than 12 items" };
          if (vErrors === null) {
            vErrors = [err24];
          } else {
            vErrors.push(err24);
          }
          errors++;
        }
        if (data6.length < 2) {
          const err25 = { instancePath: instancePath + "/components", schemaPath: "#/properties/components/minItems", keyword: "minItems", params: { limit: 2 }, message: "must NOT have fewer than 2 items" };
          if (vErrors === null) {
            vErrors = [err25];
          } else {
            vErrors.push(err25);
          }
          errors++;
        }
        const len1 = data6.length;
        for (let i1 = 0; i1 < len1; i1++) {
          if (!validate18(data6[i1], { instancePath: instancePath + "/components/" + i1, parentData: data6, parentDataProperty: i1, rootData })) {
            vErrors = vErrors === null ? validate18.errors : vErrors.concat(validate18.errors);
            errors = vErrors.length;
          }
        }
      } else {
        const err26 = { instancePath: instancePath + "/components", schemaPath: "#/properties/components/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err26];
        } else {
          vErrors.push(err26);
        }
        errors++;
      }
    }
    if (data.connections !== void 0) {
      let data8 = data.connections;
      if (Array.isArray(data8)) {
        if (data8.length > 20) {
          const err27 = { instancePath: instancePath + "/connections", schemaPath: "#/properties/connections/maxItems", keyword: "maxItems", params: { limit: 20 }, message: "must NOT have more than 20 items" };
          if (vErrors === null) {
            vErrors = [err27];
          } else {
            vErrors.push(err27);
          }
          errors++;
        }
        if (data8.length < 1) {
          const err28 = { instancePath: instancePath + "/connections", schemaPath: "#/properties/connections/minItems", keyword: "minItems", params: { limit: 1 }, message: "must NOT have fewer than 1 items" };
          if (vErrors === null) {
            vErrors = [err28];
          } else {
            vErrors.push(err28);
          }
          errors++;
        }
        const len2 = data8.length;
        for (let i2 = 0; i2 < len2; i2++) {
          let data9 = data8[i2];
          if (data9 && typeof data9 == "object" && !Array.isArray(data9)) {
            if (data9.id === void 0) {
              const err29 = { instancePath: instancePath + "/connections/" + i2, schemaPath: "#/definitions/Connection/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
              if (vErrors === null) {
                vErrors = [err29];
              } else {
                vErrors.push(err29);
              }
              errors++;
            }
            if (data9.source === void 0) {
              const err30 = { instancePath: instancePath + "/connections/" + i2, schemaPath: "#/definitions/Connection/required", keyword: "required", params: { missingProperty: "source" }, message: "must have required property 'source'" };
              if (vErrors === null) {
                vErrors = [err30];
              } else {
                vErrors.push(err30);
              }
              errors++;
            }
            if (data9.target === void 0) {
              const err31 = { instancePath: instancePath + "/connections/" + i2, schemaPath: "#/definitions/Connection/required", keyword: "required", params: { missingProperty: "target" }, message: "must have required property 'target'" };
              if (vErrors === null) {
                vErrors = [err31];
              } else {
                vErrors.push(err31);
              }
              errors++;
            }
            if (data9.label === void 0) {
              const err32 = { instancePath: instancePath + "/connections/" + i2, schemaPath: "#/definitions/Connection/required", keyword: "required", params: { missingProperty: "label" }, message: "must have required property 'label'" };
              if (vErrors === null) {
                vErrors = [err32];
              } else {
                vErrors.push(err32);
              }
              errors++;
            }
            for (const key1 in data9) {
              if (!(key1 === "id" || key1 === "source" || key1 === "target" || key1 === "label")) {
                const err33 = { instancePath: instancePath + "/connections/" + i2, schemaPath: "#/definitions/Connection/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key1 }, message: "must NOT have additional properties" };
                if (vErrors === null) {
                  vErrors = [err33];
                } else {
                  vErrors.push(err33);
                }
                errors++;
              }
            }
            if (data9.id !== void 0) {
              let data10 = data9.id;
              if (typeof data10 === "string") {
                if (func2(data10) > 64) {
                  const err34 = { instancePath: instancePath + "/connections/" + i2 + "/id", schemaPath: "#/definitions/Connection/properties/id/maxLength", keyword: "maxLength", params: { limit: 64 }, message: "must NOT have more than 64 characters" };
                  if (vErrors === null) {
                    vErrors = [err34];
                  } else {
                    vErrors.push(err34);
                  }
                  errors++;
                }
                if (func2(data10) < 1) {
                  const err35 = { instancePath: instancePath + "/connections/" + i2 + "/id", schemaPath: "#/definitions/Connection/properties/id/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                  if (vErrors === null) {
                    vErrors = [err35];
                  } else {
                    vErrors.push(err35);
                  }
                  errors++;
                }
              } else {
                const err36 = { instancePath: instancePath + "/connections/" + i2 + "/id", schemaPath: "#/definitions/Connection/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err36];
                } else {
                  vErrors.push(err36);
                }
                errors++;
              }
            }
            if (data9.source !== void 0) {
              let data11 = data9.source;
              if (typeof data11 === "string") {
                if (func2(data11) > 40) {
                  const err37 = { instancePath: instancePath + "/connections/" + i2 + "/source", schemaPath: "#/definitions/Connection/properties/source/maxLength", keyword: "maxLength", params: { limit: 40 }, message: "must NOT have more than 40 characters" };
                  if (vErrors === null) {
                    vErrors = [err37];
                  } else {
                    vErrors.push(err37);
                  }
                  errors++;
                }
              } else {
                const err38 = { instancePath: instancePath + "/connections/" + i2 + "/source", schemaPath: "#/definitions/Connection/properties/source/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err38];
                } else {
                  vErrors.push(err38);
                }
                errors++;
              }
            }
            if (data9.target !== void 0) {
              let data12 = data9.target;
              if (typeof data12 === "string") {
                if (func2(data12) > 40) {
                  const err39 = { instancePath: instancePath + "/connections/" + i2 + "/target", schemaPath: "#/definitions/Connection/properties/target/maxLength", keyword: "maxLength", params: { limit: 40 }, message: "must NOT have more than 40 characters" };
                  if (vErrors === null) {
                    vErrors = [err39];
                  } else {
                    vErrors.push(err39);
                  }
                  errors++;
                }
              } else {
                const err40 = { instancePath: instancePath + "/connections/" + i2 + "/target", schemaPath: "#/definitions/Connection/properties/target/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err40];
                } else {
                  vErrors.push(err40);
                }
                errors++;
              }
            }
            if (data9.label !== void 0) {
              let data13 = data9.label;
              if (typeof data13 === "string") {
                if (func2(data13) > 160) {
                  const err41 = { instancePath: instancePath + "/connections/" + i2 + "/label", schemaPath: "#/definitions/Connection/properties/label/maxLength", keyword: "maxLength", params: { limit: 160 }, message: "must NOT have more than 160 characters" };
                  if (vErrors === null) {
                    vErrors = [err41];
                  } else {
                    vErrors.push(err41);
                  }
                  errors++;
                }
                if (func2(data13) < 1) {
                  const err42 = { instancePath: instancePath + "/connections/" + i2 + "/label", schemaPath: "#/definitions/Connection/properties/label/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                  if (vErrors === null) {
                    vErrors = [err42];
                  } else {
                    vErrors.push(err42);
                  }
                  errors++;
                }
              } else {
                const err43 = { instancePath: instancePath + "/connections/" + i2 + "/label", schemaPath: "#/definitions/Connection/properties/label/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err43];
                } else {
                  vErrors.push(err43);
                }
                errors++;
              }
            }
          } else {
            const err44 = { instancePath: instancePath + "/connections/" + i2, schemaPath: "#/definitions/Connection/type", keyword: "type", params: { type: "object" }, message: "must be object" };
            if (vErrors === null) {
              vErrors = [err44];
            } else {
              vErrors.push(err44);
            }
            errors++;
          }
        }
      } else {
        const err45 = { instancePath: instancePath + "/connections", schemaPath: "#/properties/connections/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err45];
        } else {
          vErrors.push(err45);
        }
        errors++;
      }
    }
  } else {
    const err46 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err46];
    } else {
      vErrors.push(err46);
    }
    errors++;
  }
  validate17.errors = vErrors;
  return errors === 0;
}
function validate16(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.title === void 0) {
      const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "title" }, message: "must have required property 'title'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.summary === void 0) {
      const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "summary" }, message: "must have required property 'summary'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    if (data.businessProcess === void 0) {
      const err2 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "businessProcess" }, message: "must have required property 'businessProcess'" };
      if (vErrors === null) {
        vErrors = [err2];
      } else {
        vErrors.push(err2);
      }
      errors++;
    }
    if (data.requirements === void 0) {
      const err3 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "requirements" }, message: "must have required property 'requirements'" };
      if (vErrors === null) {
        vErrors = [err3];
      } else {
        vErrors.push(err3);
      }
      errors++;
    }
    if (data.assumptions === void 0) {
      const err4 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "assumptions" }, message: "must have required property 'assumptions'" };
      if (vErrors === null) {
        vErrors = [err4];
      } else {
        vErrors.push(err4);
      }
      errors++;
    }
    if (data.questions === void 0) {
      const err5 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "questions" }, message: "must have required property 'questions'" };
      if (vErrors === null) {
        vErrors = [err5];
      } else {
        vErrors.push(err5);
      }
      errors++;
    }
    if (data.options === void 0) {
      const err6 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "options" }, message: "must have required property 'options'" };
      if (vErrors === null) {
        vErrors = [err6];
      } else {
        vErrors.push(err6);
      }
      errors++;
    }
    if (data.recommendedOptionId === void 0) {
      const err7 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "recommendedOptionId" }, message: "must have required property 'recommendedOptionId'" };
      if (vErrors === null) {
        vErrors = [err7];
      } else {
        vErrors.push(err7);
      }
      errors++;
    }
    if (data.review === void 0) {
      const err8 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "review" }, message: "must have required property 'review'" };
      if (vErrors === null) {
        vErrors = [err8];
      } else {
        vErrors.push(err8);
      }
      errors++;
    }
    if (data.changeSummary === void 0) {
      const err9 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "changeSummary" }, message: "must have required property 'changeSummary'" };
      if (vErrors === null) {
        vErrors = [err9];
      } else {
        vErrors.push(err9);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!func24.call(schema17.properties, key0)) {
        const err10 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err10];
        } else {
          vErrors.push(err10);
        }
        errors++;
      }
    }
    if (data.title !== void 0) {
      let data0 = data.title;
      if (typeof data0 === "string") {
        if (func2(data0) > 160) {
          const err11 = { instancePath: instancePath + "/title", schemaPath: "#/properties/title/maxLength", keyword: "maxLength", params: { limit: 160 }, message: "must NOT have more than 160 characters" };
          if (vErrors === null) {
            vErrors = [err11];
          } else {
            vErrors.push(err11);
          }
          errors++;
        }
        if (func2(data0) < 1) {
          const err12 = { instancePath: instancePath + "/title", schemaPath: "#/properties/title/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
          if (vErrors === null) {
            vErrors = [err12];
          } else {
            vErrors.push(err12);
          }
          errors++;
        }
      } else {
        const err13 = { instancePath: instancePath + "/title", schemaPath: "#/properties/title/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err13];
        } else {
          vErrors.push(err13);
        }
        errors++;
      }
    }
    if (data.summary !== void 0) {
      let data1 = data.summary;
      if (typeof data1 === "string") {
        if (func2(data1) > 1800) {
          const err14 = { instancePath: instancePath + "/summary", schemaPath: "#/properties/summary/maxLength", keyword: "maxLength", params: { limit: 1800 }, message: "must NOT have more than 1800 characters" };
          if (vErrors === null) {
            vErrors = [err14];
          } else {
            vErrors.push(err14);
          }
          errors++;
        }
        if (func2(data1) < 1) {
          const err15 = { instancePath: instancePath + "/summary", schemaPath: "#/properties/summary/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
          if (vErrors === null) {
            vErrors = [err15];
          } else {
            vErrors.push(err15);
          }
          errors++;
        }
      } else {
        const err16 = { instancePath: instancePath + "/summary", schemaPath: "#/properties/summary/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err16];
        } else {
          vErrors.push(err16);
        }
        errors++;
      }
    }
    if (data.businessProcess !== void 0) {
      let data2 = data.businessProcess;
      if (Array.isArray(data2)) {
        if (data2.length > 10) {
          const err17 = { instancePath: instancePath + "/businessProcess", schemaPath: "#/properties/businessProcess/maxItems", keyword: "maxItems", params: { limit: 10 }, message: "must NOT have more than 10 items" };
          if (vErrors === null) {
            vErrors = [err17];
          } else {
            vErrors.push(err17);
          }
          errors++;
        }
        if (data2.length < 2) {
          const err18 = { instancePath: instancePath + "/businessProcess", schemaPath: "#/properties/businessProcess/minItems", keyword: "minItems", params: { limit: 2 }, message: "must NOT have fewer than 2 items" };
          if (vErrors === null) {
            vErrors = [err18];
          } else {
            vErrors.push(err18);
          }
          errors++;
        }
        const len0 = data2.length;
        for (let i0 = 0; i0 < len0; i0++) {
          let data3 = data2[i0];
          if (typeof data3 === "string") {
            if (func2(data3) > 400) {
              const err19 = { instancePath: instancePath + "/businessProcess/" + i0, schemaPath: "#/properties/businessProcess/items/maxLength", keyword: "maxLength", params: { limit: 400 }, message: "must NOT have more than 400 characters" };
              if (vErrors === null) {
                vErrors = [err19];
              } else {
                vErrors.push(err19);
              }
              errors++;
            }
          } else {
            const err20 = { instancePath: instancePath + "/businessProcess/" + i0, schemaPath: "#/properties/businessProcess/items/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err20];
            } else {
              vErrors.push(err20);
            }
            errors++;
          }
        }
      } else {
        const err21 = { instancePath: instancePath + "/businessProcess", schemaPath: "#/properties/businessProcess/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err21];
        } else {
          vErrors.push(err21);
        }
        errors++;
      }
    }
    if (data.requirements !== void 0) {
      let data4 = data.requirements;
      if (Array.isArray(data4)) {
        if (data4.length > 16) {
          const err22 = { instancePath: instancePath + "/requirements", schemaPath: "#/properties/requirements/maxItems", keyword: "maxItems", params: { limit: 16 }, message: "must NOT have more than 16 items" };
          if (vErrors === null) {
            vErrors = [err22];
          } else {
            vErrors.push(err22);
          }
          errors++;
        }
        if (data4.length < 2) {
          const err23 = { instancePath: instancePath + "/requirements", schemaPath: "#/properties/requirements/minItems", keyword: "minItems", params: { limit: 2 }, message: "must NOT have fewer than 2 items" };
          if (vErrors === null) {
            vErrors = [err23];
          } else {
            vErrors.push(err23);
          }
          errors++;
        }
        const len1 = data4.length;
        for (let i1 = 0; i1 < len1; i1++) {
          let data5 = data4[i1];
          if (data5 && typeof data5 == "object" && !Array.isArray(data5)) {
            if (data5.id === void 0) {
              const err24 = { instancePath: instancePath + "/requirements/" + i1, schemaPath: "#/definitions/Requirement/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
              if (vErrors === null) {
                vErrors = [err24];
              } else {
                vErrors.push(err24);
              }
              errors++;
            }
            if (data5.text === void 0) {
              const err25 = { instancePath: instancePath + "/requirements/" + i1, schemaPath: "#/definitions/Requirement/required", keyword: "required", params: { missingProperty: "text" }, message: "must have required property 'text'" };
              if (vErrors === null) {
                vErrors = [err25];
              } else {
                vErrors.push(err25);
              }
              errors++;
            }
            if (data5.sourceIds === void 0) {
              const err26 = { instancePath: instancePath + "/requirements/" + i1, schemaPath: "#/definitions/Requirement/required", keyword: "required", params: { missingProperty: "sourceIds" }, message: "must have required property 'sourceIds'" };
              if (vErrors === null) {
                vErrors = [err26];
              } else {
                vErrors.push(err26);
              }
              errors++;
            }
            for (const key1 in data5) {
              if (!(key1 === "id" || key1 === "text" || key1 === "sourceIds")) {
                const err27 = { instancePath: instancePath + "/requirements/" + i1, schemaPath: "#/definitions/Requirement/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key1 }, message: "must NOT have additional properties" };
                if (vErrors === null) {
                  vErrors = [err27];
                } else {
                  vErrors.push(err27);
                }
                errors++;
              }
            }
            if (data5.id !== void 0) {
              let data6 = data5.id;
              if (typeof data6 === "string") {
                if (func2(data6) > 64) {
                  const err28 = { instancePath: instancePath + "/requirements/" + i1 + "/id", schemaPath: "#/definitions/Requirement/properties/id/maxLength", keyword: "maxLength", params: { limit: 64 }, message: "must NOT have more than 64 characters" };
                  if (vErrors === null) {
                    vErrors = [err28];
                  } else {
                    vErrors.push(err28);
                  }
                  errors++;
                }
                if (func2(data6) < 1) {
                  const err29 = { instancePath: instancePath + "/requirements/" + i1 + "/id", schemaPath: "#/definitions/Requirement/properties/id/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                  if (vErrors === null) {
                    vErrors = [err29];
                  } else {
                    vErrors.push(err29);
                  }
                  errors++;
                }
              } else {
                const err30 = { instancePath: instancePath + "/requirements/" + i1 + "/id", schemaPath: "#/definitions/Requirement/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err30];
                } else {
                  vErrors.push(err30);
                }
                errors++;
              }
            }
            if (data5.text !== void 0) {
              let data7 = data5.text;
              if (typeof data7 === "string") {
                if (func2(data7) > 800) {
                  const err31 = { instancePath: instancePath + "/requirements/" + i1 + "/text", schemaPath: "#/definitions/Requirement/properties/text/maxLength", keyword: "maxLength", params: { limit: 800 }, message: "must NOT have more than 800 characters" };
                  if (vErrors === null) {
                    vErrors = [err31];
                  } else {
                    vErrors.push(err31);
                  }
                  errors++;
                }
                if (func2(data7) < 1) {
                  const err32 = { instancePath: instancePath + "/requirements/" + i1 + "/text", schemaPath: "#/definitions/Requirement/properties/text/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                  if (vErrors === null) {
                    vErrors = [err32];
                  } else {
                    vErrors.push(err32);
                  }
                  errors++;
                }
              } else {
                const err33 = { instancePath: instancePath + "/requirements/" + i1 + "/text", schemaPath: "#/definitions/Requirement/properties/text/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err33];
                } else {
                  vErrors.push(err33);
                }
                errors++;
              }
            }
            if (data5.sourceIds !== void 0) {
              let data8 = data5.sourceIds;
              if (Array.isArray(data8)) {
                if (data8.length > 6) {
                  const err34 = { instancePath: instancePath + "/requirements/" + i1 + "/sourceIds", schemaPath: "#/definitions/Requirement/properties/sourceIds/maxItems", keyword: "maxItems", params: { limit: 6 }, message: "must NOT have more than 6 items" };
                  if (vErrors === null) {
                    vErrors = [err34];
                  } else {
                    vErrors.push(err34);
                  }
                  errors++;
                }
                if (data8.length < 1) {
                  const err35 = { instancePath: instancePath + "/requirements/" + i1 + "/sourceIds", schemaPath: "#/definitions/Requirement/properties/sourceIds/minItems", keyword: "minItems", params: { limit: 1 }, message: "must NOT have fewer than 1 items" };
                  if (vErrors === null) {
                    vErrors = [err35];
                  } else {
                    vErrors.push(err35);
                  }
                  errors++;
                }
                const len2 = data8.length;
                for (let i2 = 0; i2 < len2; i2++) {
                  let data9 = data8[i2];
                  if (typeof data9 === "string") {
                    if (func2(data9) > 128) {
                      const err36 = { instancePath: instancePath + "/requirements/" + i1 + "/sourceIds/" + i2, schemaPath: "#/definitions/Requirement/properties/sourceIds/items/maxLength", keyword: "maxLength", params: { limit: 128 }, message: "must NOT have more than 128 characters" };
                      if (vErrors === null) {
                        vErrors = [err36];
                      } else {
                        vErrors.push(err36);
                      }
                      errors++;
                    }
                  } else {
                    const err37 = { instancePath: instancePath + "/requirements/" + i1 + "/sourceIds/" + i2, schemaPath: "#/definitions/Requirement/properties/sourceIds/items/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                    if (vErrors === null) {
                      vErrors = [err37];
                    } else {
                      vErrors.push(err37);
                    }
                    errors++;
                  }
                }
                let i3 = data8.length;
                let j0;
                if (i3 > 1) {
                  const indices0 = {};
                  for (; i3--; ) {
                    let item0 = data8[i3];
                    if (typeof item0 !== "string") {
                      continue;
                    }
                    if (typeof indices0[item0] == "number") {
                      j0 = indices0[item0];
                      const err38 = { instancePath: instancePath + "/requirements/" + i1 + "/sourceIds", schemaPath: "#/definitions/Requirement/properties/sourceIds/uniqueItems", keyword: "uniqueItems", params: { i: i3, j: j0 }, message: "must NOT have duplicate items (items ## " + j0 + " and " + i3 + " are identical)" };
                      if (vErrors === null) {
                        vErrors = [err38];
                      } else {
                        vErrors.push(err38);
                      }
                      errors++;
                      break;
                    }
                    indices0[item0] = i3;
                  }
                }
              } else {
                const err39 = { instancePath: instancePath + "/requirements/" + i1 + "/sourceIds", schemaPath: "#/definitions/Requirement/properties/sourceIds/type", keyword: "type", params: { type: "array" }, message: "must be array" };
                if (vErrors === null) {
                  vErrors = [err39];
                } else {
                  vErrors.push(err39);
                }
                errors++;
              }
            }
          } else {
            const err40 = { instancePath: instancePath + "/requirements/" + i1, schemaPath: "#/definitions/Requirement/type", keyword: "type", params: { type: "object" }, message: "must be object" };
            if (vErrors === null) {
              vErrors = [err40];
            } else {
              vErrors.push(err40);
            }
            errors++;
          }
        }
      } else {
        const err41 = { instancePath: instancePath + "/requirements", schemaPath: "#/properties/requirements/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err41];
        } else {
          vErrors.push(err41);
        }
        errors++;
      }
    }
    if (data.assumptions !== void 0) {
      let data10 = data.assumptions;
      if (Array.isArray(data10)) {
        if (data10.length > 10) {
          const err42 = { instancePath: instancePath + "/assumptions", schemaPath: "#/properties/assumptions/maxItems", keyword: "maxItems", params: { limit: 10 }, message: "must NOT have more than 10 items" };
          if (vErrors === null) {
            vErrors = [err42];
          } else {
            vErrors.push(err42);
          }
          errors++;
        }
        const len3 = data10.length;
        for (let i4 = 0; i4 < len3; i4++) {
          let data11 = data10[i4];
          if (typeof data11 === "string") {
            if (func2(data11) > 600) {
              const err43 = { instancePath: instancePath + "/assumptions/" + i4, schemaPath: "#/properties/assumptions/items/maxLength", keyword: "maxLength", params: { limit: 600 }, message: "must NOT have more than 600 characters" };
              if (vErrors === null) {
                vErrors = [err43];
              } else {
                vErrors.push(err43);
              }
              errors++;
            }
          } else {
            const err44 = { instancePath: instancePath + "/assumptions/" + i4, schemaPath: "#/properties/assumptions/items/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err44];
            } else {
              vErrors.push(err44);
            }
            errors++;
          }
        }
      } else {
        const err45 = { instancePath: instancePath + "/assumptions", schemaPath: "#/properties/assumptions/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err45];
        } else {
          vErrors.push(err45);
        }
        errors++;
      }
    }
    if (data.questions !== void 0) {
      let data12 = data.questions;
      if (Array.isArray(data12)) {
        if (data12.length > 6) {
          const err46 = { instancePath: instancePath + "/questions", schemaPath: "#/properties/questions/maxItems", keyword: "maxItems", params: { limit: 6 }, message: "must NOT have more than 6 items" };
          if (vErrors === null) {
            vErrors = [err46];
          } else {
            vErrors.push(err46);
          }
          errors++;
        }
        const len4 = data12.length;
        for (let i5 = 0; i5 < len4; i5++) {
          let data13 = data12[i5];
          if (data13 && typeof data13 == "object" && !Array.isArray(data13)) {
            if (data13.id === void 0) {
              const err47 = { instancePath: instancePath + "/questions/" + i5, schemaPath: "#/definitions/Question/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
              if (vErrors === null) {
                vErrors = [err47];
              } else {
                vErrors.push(err47);
              }
              errors++;
            }
            if (data13.question === void 0) {
              const err48 = { instancePath: instancePath + "/questions/" + i5, schemaPath: "#/definitions/Question/required", keyword: "required", params: { missingProperty: "question" }, message: "must have required property 'question'" };
              if (vErrors === null) {
                vErrors = [err48];
              } else {
                vErrors.push(err48);
              }
              errors++;
            }
            if (data13.why === void 0) {
              const err49 = { instancePath: instancePath + "/questions/" + i5, schemaPath: "#/definitions/Question/required", keyword: "required", params: { missingProperty: "why" }, message: "must have required property 'why'" };
              if (vErrors === null) {
                vErrors = [err49];
              } else {
                vErrors.push(err49);
              }
              errors++;
            }
            for (const key2 in data13) {
              if (!(key2 === "id" || key2 === "question" || key2 === "why")) {
                const err50 = { instancePath: instancePath + "/questions/" + i5, schemaPath: "#/definitions/Question/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key2 }, message: "must NOT have additional properties" };
                if (vErrors === null) {
                  vErrors = [err50];
                } else {
                  vErrors.push(err50);
                }
                errors++;
              }
            }
            if (data13.id !== void 0) {
              let data14 = data13.id;
              if (typeof data14 === "string") {
                if (func2(data14) > 64) {
                  const err51 = { instancePath: instancePath + "/questions/" + i5 + "/id", schemaPath: "#/definitions/Question/properties/id/maxLength", keyword: "maxLength", params: { limit: 64 }, message: "must NOT have more than 64 characters" };
                  if (vErrors === null) {
                    vErrors = [err51];
                  } else {
                    vErrors.push(err51);
                  }
                  errors++;
                }
              } else {
                const err52 = { instancePath: instancePath + "/questions/" + i5 + "/id", schemaPath: "#/definitions/Question/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err52];
                } else {
                  vErrors.push(err52);
                }
                errors++;
              }
            }
            if (data13.question !== void 0) {
              let data15 = data13.question;
              if (typeof data15 === "string") {
                if (func2(data15) > 500) {
                  const err53 = { instancePath: instancePath + "/questions/" + i5 + "/question", schemaPath: "#/definitions/Question/properties/question/maxLength", keyword: "maxLength", params: { limit: 500 }, message: "must NOT have more than 500 characters" };
                  if (vErrors === null) {
                    vErrors = [err53];
                  } else {
                    vErrors.push(err53);
                  }
                  errors++;
                }
                if (func2(data15) < 1) {
                  const err54 = { instancePath: instancePath + "/questions/" + i5 + "/question", schemaPath: "#/definitions/Question/properties/question/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                  if (vErrors === null) {
                    vErrors = [err54];
                  } else {
                    vErrors.push(err54);
                  }
                  errors++;
                }
              } else {
                const err55 = { instancePath: instancePath + "/questions/" + i5 + "/question", schemaPath: "#/definitions/Question/properties/question/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err55];
                } else {
                  vErrors.push(err55);
                }
                errors++;
              }
            }
            if (data13.why !== void 0) {
              let data16 = data13.why;
              if (typeof data16 === "string") {
                if (func2(data16) > 500) {
                  const err56 = { instancePath: instancePath + "/questions/" + i5 + "/why", schemaPath: "#/definitions/Question/properties/why/maxLength", keyword: "maxLength", params: { limit: 500 }, message: "must NOT have more than 500 characters" };
                  if (vErrors === null) {
                    vErrors = [err56];
                  } else {
                    vErrors.push(err56);
                  }
                  errors++;
                }
                if (func2(data16) < 1) {
                  const err57 = { instancePath: instancePath + "/questions/" + i5 + "/why", schemaPath: "#/definitions/Question/properties/why/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                  if (vErrors === null) {
                    vErrors = [err57];
                  } else {
                    vErrors.push(err57);
                  }
                  errors++;
                }
              } else {
                const err58 = { instancePath: instancePath + "/questions/" + i5 + "/why", schemaPath: "#/definitions/Question/properties/why/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err58];
                } else {
                  vErrors.push(err58);
                }
                errors++;
              }
            }
          } else {
            const err59 = { instancePath: instancePath + "/questions/" + i5, schemaPath: "#/definitions/Question/type", keyword: "type", params: { type: "object" }, message: "must be object" };
            if (vErrors === null) {
              vErrors = [err59];
            } else {
              vErrors.push(err59);
            }
            errors++;
          }
        }
      } else {
        const err60 = { instancePath: instancePath + "/questions", schemaPath: "#/properties/questions/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err60];
        } else {
          vErrors.push(err60);
        }
        errors++;
      }
    }
    if (data.options !== void 0) {
      let data17 = data.options;
      if (Array.isArray(data17)) {
        if (data17.length > 3) {
          const err61 = { instancePath: instancePath + "/options", schemaPath: "#/properties/options/maxItems", keyword: "maxItems", params: { limit: 3 }, message: "must NOT have more than 3 items" };
          if (vErrors === null) {
            vErrors = [err61];
          } else {
            vErrors.push(err61);
          }
          errors++;
        }
        if (data17.length < 2) {
          const err62 = { instancePath: instancePath + "/options", schemaPath: "#/properties/options/minItems", keyword: "minItems", params: { limit: 2 }, message: "must NOT have fewer than 2 items" };
          if (vErrors === null) {
            vErrors = [err62];
          } else {
            vErrors.push(err62);
          }
          errors++;
        }
        const len5 = data17.length;
        for (let i6 = 0; i6 < len5; i6++) {
          if (!validate17(data17[i6], { instancePath: instancePath + "/options/" + i6, parentData: data17, parentDataProperty: i6, rootData })) {
            vErrors = vErrors === null ? validate17.errors : vErrors.concat(validate17.errors);
            errors = vErrors.length;
          }
        }
      } else {
        const err63 = { instancePath: instancePath + "/options", schemaPath: "#/properties/options/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err63];
        } else {
          vErrors.push(err63);
        }
        errors++;
      }
    }
    if (data.recommendedOptionId !== void 0) {
      let data19 = data.recommendedOptionId;
      if (typeof data19 === "string") {
        if (func2(data19) > 40) {
          const err64 = { instancePath: instancePath + "/recommendedOptionId", schemaPath: "#/properties/recommendedOptionId/maxLength", keyword: "maxLength", params: { limit: 40 }, message: "must NOT have more than 40 characters" };
          if (vErrors === null) {
            vErrors = [err64];
          } else {
            vErrors.push(err64);
          }
          errors++;
        }
      } else {
        const err65 = { instancePath: instancePath + "/recommendedOptionId", schemaPath: "#/properties/recommendedOptionId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err65];
        } else {
          vErrors.push(err65);
        }
        errors++;
      }
    }
    if (data.review !== void 0) {
      let data20 = data.review;
      if (Array.isArray(data20)) {
        if (data20.length > 9) {
          const err66 = { instancePath: instancePath + "/review", schemaPath: "#/properties/review/maxItems", keyword: "maxItems", params: { limit: 9 }, message: "must NOT have more than 9 items" };
          if (vErrors === null) {
            vErrors = [err66];
          } else {
            vErrors.push(err66);
          }
          errors++;
        }
        if (data20.length < 9) {
          const err67 = { instancePath: instancePath + "/review", schemaPath: "#/properties/review/minItems", keyword: "minItems", params: { limit: 9 }, message: "must NOT have fewer than 9 items" };
          if (vErrors === null) {
            vErrors = [err67];
          } else {
            vErrors.push(err67);
          }
          errors++;
        }
        const len6 = data20.length;
        for (let i7 = 0; i7 < len6; i7++) {
          let data21 = data20[i7];
          if (data21 && typeof data21 == "object" && !Array.isArray(data21)) {
            if (data21.dimension === void 0) {
              const err68 = { instancePath: instancePath + "/review/" + i7, schemaPath: "#/definitions/ReviewFinding/required", keyword: "required", params: { missingProperty: "dimension" }, message: "must have required property 'dimension'" };
              if (vErrors === null) {
                vErrors = [err68];
              } else {
                vErrors.push(err68);
              }
              errors++;
            }
            if (data21.severity === void 0) {
              const err69 = { instancePath: instancePath + "/review/" + i7, schemaPath: "#/definitions/ReviewFinding/required", keyword: "required", params: { missingProperty: "severity" }, message: "must have required property 'severity'" };
              if (vErrors === null) {
                vErrors = [err69];
              } else {
                vErrors.push(err69);
              }
              errors++;
            }
            if (data21.finding === void 0) {
              const err70 = { instancePath: instancePath + "/review/" + i7, schemaPath: "#/definitions/ReviewFinding/required", keyword: "required", params: { missingProperty: "finding" }, message: "must have required property 'finding'" };
              if (vErrors === null) {
                vErrors = [err70];
              } else {
                vErrors.push(err70);
              }
              errors++;
            }
            if (data21.recommendation === void 0) {
              const err71 = { instancePath: instancePath + "/review/" + i7, schemaPath: "#/definitions/ReviewFinding/required", keyword: "required", params: { missingProperty: "recommendation" }, message: "must have required property 'recommendation'" };
              if (vErrors === null) {
                vErrors = [err71];
              } else {
                vErrors.push(err71);
              }
              errors++;
            }
            if (data21.sourceIds === void 0) {
              const err72 = { instancePath: instancePath + "/review/" + i7, schemaPath: "#/definitions/ReviewFinding/required", keyword: "required", params: { missingProperty: "sourceIds" }, message: "must have required property 'sourceIds'" };
              if (vErrors === null) {
                vErrors = [err72];
              } else {
                vErrors.push(err72);
              }
              errors++;
            }
            for (const key3 in data21) {
              if (!(key3 === "dimension" || key3 === "severity" || key3 === "finding" || key3 === "recommendation" || key3 === "sourceIds")) {
                const err73 = { instancePath: instancePath + "/review/" + i7, schemaPath: "#/definitions/ReviewFinding/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key3 }, message: "must NOT have additional properties" };
                if (vErrors === null) {
                  vErrors = [err73];
                } else {
                  vErrors.push(err73);
                }
                errors++;
              }
            }
            if (data21.dimension !== void 0) {
              let data22 = data21.dimension;
              if (typeof data22 !== "string") {
                const err74 = { instancePath: instancePath + "/review/" + i7 + "/dimension", schemaPath: "#/definitions/ReviewFinding/properties/dimension/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err74];
                } else {
                  vErrors.push(err74);
                }
                errors++;
              }
              if (!(data22 === "business" || data22 === "security" || data22 === "reliability" || data22 === "performance" || data22 === "cost" || data22 === "integration" || data22 === "compliance" || data22 === "operations" || data22 === "delivery")) {
                const err75 = { instancePath: instancePath + "/review/" + i7 + "/dimension", schemaPath: "#/definitions/ReviewFinding/properties/dimension/enum", keyword: "enum", params: { allowedValues: schema16.properties.dimension.enum }, message: "must be equal to one of the allowed values" };
                if (vErrors === null) {
                  vErrors = [err75];
                } else {
                  vErrors.push(err75);
                }
                errors++;
              }
            }
            if (data21.severity !== void 0) {
              let data23 = data21.severity;
              if (typeof data23 !== "string") {
                const err76 = { instancePath: instancePath + "/review/" + i7 + "/severity", schemaPath: "#/definitions/ReviewFinding/properties/severity/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err76];
                } else {
                  vErrors.push(err76);
                }
                errors++;
              }
              if (!(data23 === "info" || data23 === "warning" || data23 === "blocker")) {
                const err77 = { instancePath: instancePath + "/review/" + i7 + "/severity", schemaPath: "#/definitions/ReviewFinding/properties/severity/enum", keyword: "enum", params: { allowedValues: schema16.properties.severity.enum }, message: "must be equal to one of the allowed values" };
                if (vErrors === null) {
                  vErrors = [err77];
                } else {
                  vErrors.push(err77);
                }
                errors++;
              }
            }
            if (data21.finding !== void 0) {
              let data24 = data21.finding;
              if (typeof data24 === "string") {
                if (func2(data24) > 1e3) {
                  const err78 = { instancePath: instancePath + "/review/" + i7 + "/finding", schemaPath: "#/definitions/ReviewFinding/properties/finding/maxLength", keyword: "maxLength", params: { limit: 1e3 }, message: "must NOT have more than 1000 characters" };
                  if (vErrors === null) {
                    vErrors = [err78];
                  } else {
                    vErrors.push(err78);
                  }
                  errors++;
                }
                if (func2(data24) < 1) {
                  const err79 = { instancePath: instancePath + "/review/" + i7 + "/finding", schemaPath: "#/definitions/ReviewFinding/properties/finding/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                  if (vErrors === null) {
                    vErrors = [err79];
                  } else {
                    vErrors.push(err79);
                  }
                  errors++;
                }
              } else {
                const err80 = { instancePath: instancePath + "/review/" + i7 + "/finding", schemaPath: "#/definitions/ReviewFinding/properties/finding/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err80];
                } else {
                  vErrors.push(err80);
                }
                errors++;
              }
            }
            if (data21.recommendation !== void 0) {
              let data25 = data21.recommendation;
              if (typeof data25 === "string") {
                if (func2(data25) > 1e3) {
                  const err81 = { instancePath: instancePath + "/review/" + i7 + "/recommendation", schemaPath: "#/definitions/ReviewFinding/properties/recommendation/maxLength", keyword: "maxLength", params: { limit: 1e3 }, message: "must NOT have more than 1000 characters" };
                  if (vErrors === null) {
                    vErrors = [err81];
                  } else {
                    vErrors.push(err81);
                  }
                  errors++;
                }
                if (func2(data25) < 1) {
                  const err82 = { instancePath: instancePath + "/review/" + i7 + "/recommendation", schemaPath: "#/definitions/ReviewFinding/properties/recommendation/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                  if (vErrors === null) {
                    vErrors = [err82];
                  } else {
                    vErrors.push(err82);
                  }
                  errors++;
                }
              } else {
                const err83 = { instancePath: instancePath + "/review/" + i7 + "/recommendation", schemaPath: "#/definitions/ReviewFinding/properties/recommendation/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err83];
                } else {
                  vErrors.push(err83);
                }
                errors++;
              }
            }
            if (data21.sourceIds !== void 0) {
              let data26 = data21.sourceIds;
              if (Array.isArray(data26)) {
                if (data26.length > 6) {
                  const err84 = { instancePath: instancePath + "/review/" + i7 + "/sourceIds", schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/maxItems", keyword: "maxItems", params: { limit: 6 }, message: "must NOT have more than 6 items" };
                  if (vErrors === null) {
                    vErrors = [err84];
                  } else {
                    vErrors.push(err84);
                  }
                  errors++;
                }
                if (data26.length < 1) {
                  const err85 = { instancePath: instancePath + "/review/" + i7 + "/sourceIds", schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/minItems", keyword: "minItems", params: { limit: 1 }, message: "must NOT have fewer than 1 items" };
                  if (vErrors === null) {
                    vErrors = [err85];
                  } else {
                    vErrors.push(err85);
                  }
                  errors++;
                }
                const len7 = data26.length;
                for (let i8 = 0; i8 < len7; i8++) {
                  let data27 = data26[i8];
                  if (typeof data27 === "string") {
                    if (func2(data27) > 128) {
                      const err86 = { instancePath: instancePath + "/review/" + i7 + "/sourceIds/" + i8, schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/items/maxLength", keyword: "maxLength", params: { limit: 128 }, message: "must NOT have more than 128 characters" };
                      if (vErrors === null) {
                        vErrors = [err86];
                      } else {
                        vErrors.push(err86);
                      }
                      errors++;
                    }
                  } else {
                    const err87 = { instancePath: instancePath + "/review/" + i7 + "/sourceIds/" + i8, schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/items/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                    if (vErrors === null) {
                      vErrors = [err87];
                    } else {
                      vErrors.push(err87);
                    }
                    errors++;
                  }
                }
                let i9 = data26.length;
                let j1;
                if (i9 > 1) {
                  const indices1 = {};
                  for (; i9--; ) {
                    let item1 = data26[i9];
                    if (typeof item1 !== "string") {
                      continue;
                    }
                    if (typeof indices1[item1] == "number") {
                      j1 = indices1[item1];
                      const err88 = { instancePath: instancePath + "/review/" + i7 + "/sourceIds", schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/uniqueItems", keyword: "uniqueItems", params: { i: i9, j: j1 }, message: "must NOT have duplicate items (items ## " + j1 + " and " + i9 + " are identical)" };
                      if (vErrors === null) {
                        vErrors = [err88];
                      } else {
                        vErrors.push(err88);
                      }
                      errors++;
                      break;
                    }
                    indices1[item1] = i9;
                  }
                }
              } else {
                const err89 = { instancePath: instancePath + "/review/" + i7 + "/sourceIds", schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/type", keyword: "type", params: { type: "array" }, message: "must be array" };
                if (vErrors === null) {
                  vErrors = [err89];
                } else {
                  vErrors.push(err89);
                }
                errors++;
              }
            }
          } else {
            const err90 = { instancePath: instancePath + "/review/" + i7, schemaPath: "#/definitions/ReviewFinding/type", keyword: "type", params: { type: "object" }, message: "must be object" };
            if (vErrors === null) {
              vErrors = [err90];
            } else {
              vErrors.push(err90);
            }
            errors++;
          }
        }
      } else {
        const err91 = { instancePath: instancePath + "/review", schemaPath: "#/properties/review/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err91];
        } else {
          vErrors.push(err91);
        }
        errors++;
      }
    }
    if (data.changeSummary !== void 0) {
      let data28 = data.changeSummary;
      if (typeof data28 === "string") {
        if (func2(data28) > 1e3) {
          const err92 = { instancePath: instancePath + "/changeSummary", schemaPath: "#/properties/changeSummary/maxLength", keyword: "maxLength", params: { limit: 1e3 }, message: "must NOT have more than 1000 characters" };
          if (vErrors === null) {
            vErrors = [err92];
          } else {
            vErrors.push(err92);
          }
          errors++;
        }
        if (func2(data28) < 1) {
          const err93 = { instancePath: instancePath + "/changeSummary", schemaPath: "#/properties/changeSummary/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
          if (vErrors === null) {
            vErrors = [err93];
          } else {
            vErrors.push(err93);
          }
          errors++;
        }
      } else {
        const err94 = { instancePath: instancePath + "/changeSummary", schemaPath: "#/properties/changeSummary/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err94];
        } else {
          vErrors.push(err94);
        }
        errors++;
      }
    }
  } else {
    const err95 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err95];
    } else {
      vErrors.push(err95);
    }
    errors++;
  }
  validate16.errors = vErrors;
  return errors === 0;
}
function validate23(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.resultId === void 0) {
      const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "resultId" }, message: "must have required property 'resultId'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.inputHash === void 0) {
      const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "inputHash" }, message: "must have required property 'inputHash'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    if (data.createdAt === void 0) {
      const err2 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "createdAt" }, message: "must have required property 'createdAt'" };
      if (vErrors === null) {
        vErrors = [err2];
      } else {
        vErrors.push(err2);
      }
      errors++;
    }
    if (data.origin === void 0) {
      const err3 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "origin" }, message: "must have required property 'origin'" };
      if (vErrors === null) {
        vErrors = [err3];
      } else {
        vErrors.push(err3);
      }
      errors++;
    }
    if (data.analysis === void 0) {
      const err4 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "analysis" }, message: "must have required property 'analysis'" };
      if (vErrors === null) {
        vErrors = [err4];
      } else {
        vErrors.push(err4);
      }
      errors++;
    }
    if (data.modelReceipts === void 0) {
      const err5 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "modelReceipts" }, message: "must have required property 'modelReceipts'" };
      if (vErrors === null) {
        vErrors = [err5];
      } else {
        vErrors.push(err5);
      }
      errors++;
    }
    if (data.sources === void 0) {
      const err6 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "sources" }, message: "must have required property 'sources'" };
      if (vErrors === null) {
        vErrors = [err6];
      } else {
        vErrors.push(err6);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!(key0 === "resultId" || key0 === "inputHash" || key0 === "createdAt" || key0 === "origin" || key0 === "analysis" || key0 === "modelReceipts" || key0 === "sources")) {
        const err7 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err7];
        } else {
          vErrors.push(err7);
        }
        errors++;
      }
    }
    if (data.resultId !== void 0) {
      if (typeof data.resultId !== "string") {
        const err8 = { instancePath: instancePath + "/resultId", schemaPath: "#/properties/resultId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err8];
        } else {
          vErrors.push(err8);
        }
        errors++;
      }
    }
    if (data.inputHash !== void 0) {
      if (typeof data.inputHash !== "string") {
        const err9 = { instancePath: instancePath + "/inputHash", schemaPath: "#/properties/inputHash/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err9];
        } else {
          vErrors.push(err9);
        }
        errors++;
      }
    }
    if (data.createdAt !== void 0) {
      if (typeof data.createdAt !== "string") {
        const err10 = { instancePath: instancePath + "/createdAt", schemaPath: "#/properties/createdAt/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err10];
        } else {
          vErrors.push(err10);
        }
        errors++;
      }
    }
    if (data.origin !== void 0) {
      let data3 = data.origin;
      if (typeof data3 !== "string") {
        const err11 = { instancePath: instancePath + "/origin", schemaPath: "#/properties/origin/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err11];
        } else {
          vErrors.push(err11);
        }
        errors++;
      }
      if ("live-model" !== data3) {
        const err12 = { instancePath: instancePath + "/origin", schemaPath: "#/properties/origin/const", keyword: "const", params: { allowedValue: "live-model" }, message: "must be equal to constant" };
        if (vErrors === null) {
          vErrors = [err12];
        } else {
          vErrors.push(err12);
        }
        errors++;
      }
    }
    if (data.analysis !== void 0) {
      if (!validate16(data.analysis, { instancePath: instancePath + "/analysis", parentData: data, parentDataProperty: "analysis", rootData })) {
        vErrors = vErrors === null ? validate16.errors : vErrors.concat(validate16.errors);
        errors = vErrors.length;
      }
    }
    if (data.modelReceipts !== void 0) {
      let data5 = data.modelReceipts;
      if (Array.isArray(data5)) {
        if (data5.length > 2) {
          const err13 = { instancePath: instancePath + "/modelReceipts", schemaPath: "#/properties/modelReceipts/maxItems", keyword: "maxItems", params: { limit: 2 }, message: "must NOT have more than 2 items" };
          if (vErrors === null) {
            vErrors = [err13];
          } else {
            vErrors.push(err13);
          }
          errors++;
        }
        if (data5.length < 2) {
          const err14 = { instancePath: instancePath + "/modelReceipts", schemaPath: "#/properties/modelReceipts/minItems", keyword: "minItems", params: { limit: 2 }, message: "must NOT have fewer than 2 items" };
          if (vErrors === null) {
            vErrors = [err14];
          } else {
            vErrors.push(err14);
          }
          errors++;
        }
        const len0 = data5.length;
        for (let i0 = 0; i0 < len0; i0++) {
          let data6 = data5[i0];
          if (data6 && typeof data6 == "object" && !Array.isArray(data6)) {
            if (data6.role === void 0) {
              const err15 = { instancePath: instancePath + "/modelReceipts/" + i0, schemaPath: "#/definitions/ModelReceipt/required", keyword: "required", params: { missingProperty: "role" }, message: "must have required property 'role'" };
              if (vErrors === null) {
                vErrors = [err15];
              } else {
                vErrors.push(err15);
              }
              errors++;
            }
            if (data6.model === void 0) {
              const err16 = { instancePath: instancePath + "/modelReceipts/" + i0, schemaPath: "#/definitions/ModelReceipt/required", keyword: "required", params: { missingProperty: "model" }, message: "must have required property 'model'" };
              if (vErrors === null) {
                vErrors = [err16];
              } else {
                vErrors.push(err16);
              }
              errors++;
            }
            if (data6.responseId === void 0) {
              const err17 = { instancePath: instancePath + "/modelReceipts/" + i0, schemaPath: "#/definitions/ModelReceipt/required", keyword: "required", params: { missingProperty: "responseId" }, message: "must have required property 'responseId'" };
              if (vErrors === null) {
                vErrors = [err17];
              } else {
                vErrors.push(err17);
              }
              errors++;
            }
            if (data6.durationMs === void 0) {
              const err18 = { instancePath: instancePath + "/modelReceipts/" + i0, schemaPath: "#/definitions/ModelReceipt/required", keyword: "required", params: { missingProperty: "durationMs" }, message: "must have required property 'durationMs'" };
              if (vErrors === null) {
                vErrors = [err18];
              } else {
                vErrors.push(err18);
              }
              errors++;
            }
            for (const key1 in data6) {
              if (!(key1 === "role" || key1 === "model" || key1 === "responseId" || key1 === "durationMs")) {
                const err19 = { instancePath: instancePath + "/modelReceipts/" + i0, schemaPath: "#/definitions/ModelReceipt/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key1 }, message: "must NOT have additional properties" };
                if (vErrors === null) {
                  vErrors = [err19];
                } else {
                  vErrors.push(err19);
                }
                errors++;
              }
            }
            if (data6.role !== void 0) {
              let data7 = data6.role;
              if (typeof data7 !== "string") {
                const err20 = { instancePath: instancePath + "/modelReceipts/" + i0 + "/role", schemaPath: "#/definitions/ModelReceipt/properties/role/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err20];
                } else {
                  vErrors.push(err20);
                }
                errors++;
              }
              if (!(data7 === "synthesis" || data7 === "assurance")) {
                const err21 = { instancePath: instancePath + "/modelReceipts/" + i0 + "/role", schemaPath: "#/definitions/ModelReceipt/properties/role/enum", keyword: "enum", params: { allowedValues: schema28.properties.role.enum }, message: "must be equal to one of the allowed values" };
                if (vErrors === null) {
                  vErrors = [err21];
                } else {
                  vErrors.push(err21);
                }
                errors++;
              }
            }
            if (data6.model !== void 0) {
              if (typeof data6.model !== "string") {
                const err22 = { instancePath: instancePath + "/modelReceipts/" + i0 + "/model", schemaPath: "#/definitions/ModelReceipt/properties/model/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err22];
                } else {
                  vErrors.push(err22);
                }
                errors++;
              }
            }
            if (data6.responseId !== void 0) {
              let data9 = data6.responseId;
              if (typeof data9 === "string") {
                if (func2(data9) < 1) {
                  const err23 = { instancePath: instancePath + "/modelReceipts/" + i0 + "/responseId", schemaPath: "#/definitions/ModelReceipt/properties/responseId/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                  if (vErrors === null) {
                    vErrors = [err23];
                  } else {
                    vErrors.push(err23);
                  }
                  errors++;
                }
              } else {
                const err24 = { instancePath: instancePath + "/modelReceipts/" + i0 + "/responseId", schemaPath: "#/definitions/ModelReceipt/properties/responseId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err24];
                } else {
                  vErrors.push(err24);
                }
                errors++;
              }
            }
            if (data6.durationMs !== void 0) {
              let data10 = data6.durationMs;
              if (!(typeof data10 == "number" && (!(data10 % 1) && !isNaN(data10)))) {
                const err25 = { instancePath: instancePath + "/modelReceipts/" + i0 + "/durationMs", schemaPath: "#/definitions/ModelReceipt/properties/durationMs/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                if (vErrors === null) {
                  vErrors = [err25];
                } else {
                  vErrors.push(err25);
                }
                errors++;
              }
              if (typeof data10 == "number") {
                if (data10 < 0 || isNaN(data10)) {
                  const err26 = { instancePath: instancePath + "/modelReceipts/" + i0 + "/durationMs", schemaPath: "#/definitions/ModelReceipt/properties/durationMs/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
                  if (vErrors === null) {
                    vErrors = [err26];
                  } else {
                    vErrors.push(err26);
                  }
                  errors++;
                }
              }
            }
          } else {
            const err27 = { instancePath: instancePath + "/modelReceipts/" + i0, schemaPath: "#/definitions/ModelReceipt/type", keyword: "type", params: { type: "object" }, message: "must be object" };
            if (vErrors === null) {
              vErrors = [err27];
            } else {
              vErrors.push(err27);
            }
            errors++;
          }
        }
      } else {
        const err28 = { instancePath: instancePath + "/modelReceipts", schemaPath: "#/properties/modelReceipts/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err28];
        } else {
          vErrors.push(err28);
        }
        errors++;
      }
    }
    if (data.sources !== void 0) {
      let data11 = data.sources;
      if (Array.isArray(data11)) {
        const len1 = data11.length;
        for (let i1 = 0; i1 < len1; i1++) {
          let data12 = data11[i1];
          if (data12 && typeof data12 == "object" && !Array.isArray(data12)) {
            if (data12.id === void 0) {
              const err29 = { instancePath: instancePath + "/sources/" + i1, schemaPath: "#/properties/sources/items/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
              if (vErrors === null) {
                vErrors = [err29];
              } else {
                vErrors.push(err29);
              }
              errors++;
            }
            if (data12.name === void 0) {
              const err30 = { instancePath: instancePath + "/sources/" + i1, schemaPath: "#/properties/sources/items/required", keyword: "required", params: { missingProperty: "name" }, message: "must have required property 'name'" };
              if (vErrors === null) {
                vErrors = [err30];
              } else {
                vErrors.push(err30);
              }
              errors++;
            }
            for (const key2 in data12) {
              if (!(key2 === "id" || key2 === "name")) {
                const err31 = { instancePath: instancePath + "/sources/" + i1, schemaPath: "#/properties/sources/items/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key2 }, message: "must NOT have additional properties" };
                if (vErrors === null) {
                  vErrors = [err31];
                } else {
                  vErrors.push(err31);
                }
                errors++;
              }
            }
            if (data12.id !== void 0) {
              if (typeof data12.id !== "string") {
                const err32 = { instancePath: instancePath + "/sources/" + i1 + "/id", schemaPath: "#/properties/sources/items/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err32];
                } else {
                  vErrors.push(err32);
                }
                errors++;
              }
            }
            if (data12.name !== void 0) {
              if (typeof data12.name !== "string") {
                const err33 = { instancePath: instancePath + "/sources/" + i1 + "/name", schemaPath: "#/properties/sources/items/properties/name/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err33];
                } else {
                  vErrors.push(err33);
                }
                errors++;
              }
            }
          } else {
            const err34 = { instancePath: instancePath + "/sources/" + i1, schemaPath: "#/properties/sources/items/type", keyword: "type", params: { type: "object" }, message: "must be object" };
            if (vErrors === null) {
              vErrors = [err34];
            } else {
              vErrors.push(err34);
            }
            errors++;
          }
        }
      } else {
        const err35 = { instancePath: instancePath + "/sources", schemaPath: "#/properties/sources/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err35];
        } else {
          vErrors.push(err35);
        }
        errors++;
      }
    }
  } else {
    const err36 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err36];
    } else {
      vErrors.push(err36);
    }
    errors++;
  }
  validate23.errors = vErrors;
  return errors === 0;
}
var schema30 = { "type": "object", "additionalProperties": false, "description": "Server-bound demo-human authorization to generate and independently review a revision; not sign-off of its result.", "properties": { "baseResultId": { "type": "string", "minLength": 1, "maxLength": 80 }, "baseResultHash": { "type": "string", "pattern": "^[a-f0-9]{64}$" }, "optionId": { "$ref": "#/definitions/DesignChange/properties/optionId" }, "finding": { "$ref": "#/definitions/ReviewFinding" }, "intent": { "$ref": "#/definitions/DesignChange/properties/intent" }, "instruction": { "type": "string", "minLength": 10, "maxLength": 2e3 }, "refinement": { "type": "string", "minLength": 10, "maxLength": 4e3 }, "approvedAt": { "type": "string", "format": "date-time" }, "actor": { "type": "string", "const": "demo-human" }, "scope": { "type": "string", "const": "design-revision-only" } }, "required": ["baseResultId", "baseResultHash", "optionId", "finding", "intent", "instruction", "refinement", "approvedAt", "actor", "scope"] };
var schema33 = { "type": "string", "enum": ["recommendation", "challenge"] };
var pattern3 = new RegExp("^[a-f0-9]{64}$", "u");
var formats0 = require_formats().fullFormats["date-time"];
function validate26(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.baseResultId === void 0) {
      const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "baseResultId" }, message: "must have required property 'baseResultId'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.baseResultHash === void 0) {
      const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "baseResultHash" }, message: "must have required property 'baseResultHash'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    if (data.optionId === void 0) {
      const err2 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "optionId" }, message: "must have required property 'optionId'" };
      if (vErrors === null) {
        vErrors = [err2];
      } else {
        vErrors.push(err2);
      }
      errors++;
    }
    if (data.finding === void 0) {
      const err3 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "finding" }, message: "must have required property 'finding'" };
      if (vErrors === null) {
        vErrors = [err3];
      } else {
        vErrors.push(err3);
      }
      errors++;
    }
    if (data.intent === void 0) {
      const err4 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "intent" }, message: "must have required property 'intent'" };
      if (vErrors === null) {
        vErrors = [err4];
      } else {
        vErrors.push(err4);
      }
      errors++;
    }
    if (data.instruction === void 0) {
      const err5 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "instruction" }, message: "must have required property 'instruction'" };
      if (vErrors === null) {
        vErrors = [err5];
      } else {
        vErrors.push(err5);
      }
      errors++;
    }
    if (data.refinement === void 0) {
      const err6 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "refinement" }, message: "must have required property 'refinement'" };
      if (vErrors === null) {
        vErrors = [err6];
      } else {
        vErrors.push(err6);
      }
      errors++;
    }
    if (data.approvedAt === void 0) {
      const err7 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "approvedAt" }, message: "must have required property 'approvedAt'" };
      if (vErrors === null) {
        vErrors = [err7];
      } else {
        vErrors.push(err7);
      }
      errors++;
    }
    if (data.actor === void 0) {
      const err8 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "actor" }, message: "must have required property 'actor'" };
      if (vErrors === null) {
        vErrors = [err8];
      } else {
        vErrors.push(err8);
      }
      errors++;
    }
    if (data.scope === void 0) {
      const err9 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "scope" }, message: "must have required property 'scope'" };
      if (vErrors === null) {
        vErrors = [err9];
      } else {
        vErrors.push(err9);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!func24.call(schema30.properties, key0)) {
        const err10 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err10];
        } else {
          vErrors.push(err10);
        }
        errors++;
      }
    }
    if (data.baseResultId !== void 0) {
      let data0 = data.baseResultId;
      if (typeof data0 === "string") {
        if (func2(data0) > 80) {
          const err11 = { instancePath: instancePath + "/baseResultId", schemaPath: "#/properties/baseResultId/maxLength", keyword: "maxLength", params: { limit: 80 }, message: "must NOT have more than 80 characters" };
          if (vErrors === null) {
            vErrors = [err11];
          } else {
            vErrors.push(err11);
          }
          errors++;
        }
        if (func2(data0) < 1) {
          const err12 = { instancePath: instancePath + "/baseResultId", schemaPath: "#/properties/baseResultId/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
          if (vErrors === null) {
            vErrors = [err12];
          } else {
            vErrors.push(err12);
          }
          errors++;
        }
      } else {
        const err13 = { instancePath: instancePath + "/baseResultId", schemaPath: "#/properties/baseResultId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err13];
        } else {
          vErrors.push(err13);
        }
        errors++;
      }
    }
    if (data.baseResultHash !== void 0) {
      let data1 = data.baseResultHash;
      if (typeof data1 === "string") {
        if (!pattern3.test(data1)) {
          const err14 = { instancePath: instancePath + "/baseResultHash", schemaPath: "#/properties/baseResultHash/pattern", keyword: "pattern", params: { pattern: "^[a-f0-9]{64}$" }, message: 'must match pattern "^[a-f0-9]{64}$"' };
          if (vErrors === null) {
            vErrors = [err14];
          } else {
            vErrors.push(err14);
          }
          errors++;
        }
      } else {
        const err15 = { instancePath: instancePath + "/baseResultHash", schemaPath: "#/properties/baseResultHash/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err15];
        } else {
          vErrors.push(err15);
        }
        errors++;
      }
    }
    if (data.optionId !== void 0) {
      let data2 = data.optionId;
      if (typeof data2 === "string") {
        if (!pattern0.test(data2)) {
          const err16 = { instancePath: instancePath + "/optionId", schemaPath: "#/definitions/DesignChange/properties/optionId/pattern", keyword: "pattern", params: { pattern: "^[a-z][a-z0-9-]{0,39}$" }, message: 'must match pattern "^[a-z][a-z0-9-]{0,39}$"' };
          if (vErrors === null) {
            vErrors = [err16];
          } else {
            vErrors.push(err16);
          }
          errors++;
        }
      } else {
        const err17 = { instancePath: instancePath + "/optionId", schemaPath: "#/definitions/DesignChange/properties/optionId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err17];
        } else {
          vErrors.push(err17);
        }
        errors++;
      }
    }
    if (data.finding !== void 0) {
      let data3 = data.finding;
      if (data3 && typeof data3 == "object" && !Array.isArray(data3)) {
        if (data3.dimension === void 0) {
          const err18 = { instancePath: instancePath + "/finding", schemaPath: "#/definitions/ReviewFinding/required", keyword: "required", params: { missingProperty: "dimension" }, message: "must have required property 'dimension'" };
          if (vErrors === null) {
            vErrors = [err18];
          } else {
            vErrors.push(err18);
          }
          errors++;
        }
        if (data3.severity === void 0) {
          const err19 = { instancePath: instancePath + "/finding", schemaPath: "#/definitions/ReviewFinding/required", keyword: "required", params: { missingProperty: "severity" }, message: "must have required property 'severity'" };
          if (vErrors === null) {
            vErrors = [err19];
          } else {
            vErrors.push(err19);
          }
          errors++;
        }
        if (data3.finding === void 0) {
          const err20 = { instancePath: instancePath + "/finding", schemaPath: "#/definitions/ReviewFinding/required", keyword: "required", params: { missingProperty: "finding" }, message: "must have required property 'finding'" };
          if (vErrors === null) {
            vErrors = [err20];
          } else {
            vErrors.push(err20);
          }
          errors++;
        }
        if (data3.recommendation === void 0) {
          const err21 = { instancePath: instancePath + "/finding", schemaPath: "#/definitions/ReviewFinding/required", keyword: "required", params: { missingProperty: "recommendation" }, message: "must have required property 'recommendation'" };
          if (vErrors === null) {
            vErrors = [err21];
          } else {
            vErrors.push(err21);
          }
          errors++;
        }
        if (data3.sourceIds === void 0) {
          const err22 = { instancePath: instancePath + "/finding", schemaPath: "#/definitions/ReviewFinding/required", keyword: "required", params: { missingProperty: "sourceIds" }, message: "must have required property 'sourceIds'" };
          if (vErrors === null) {
            vErrors = [err22];
          } else {
            vErrors.push(err22);
          }
          errors++;
        }
        for (const key1 in data3) {
          if (!(key1 === "dimension" || key1 === "severity" || key1 === "finding" || key1 === "recommendation" || key1 === "sourceIds")) {
            const err23 = { instancePath: instancePath + "/finding", schemaPath: "#/definitions/ReviewFinding/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key1 }, message: "must NOT have additional properties" };
            if (vErrors === null) {
              vErrors = [err23];
            } else {
              vErrors.push(err23);
            }
            errors++;
          }
        }
        if (data3.dimension !== void 0) {
          let data4 = data3.dimension;
          if (typeof data4 !== "string") {
            const err24 = { instancePath: instancePath + "/finding/dimension", schemaPath: "#/definitions/ReviewFinding/properties/dimension/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err24];
            } else {
              vErrors.push(err24);
            }
            errors++;
          }
          if (!(data4 === "business" || data4 === "security" || data4 === "reliability" || data4 === "performance" || data4 === "cost" || data4 === "integration" || data4 === "compliance" || data4 === "operations" || data4 === "delivery")) {
            const err25 = { instancePath: instancePath + "/finding/dimension", schemaPath: "#/definitions/ReviewFinding/properties/dimension/enum", keyword: "enum", params: { allowedValues: schema16.properties.dimension.enum }, message: "must be equal to one of the allowed values" };
            if (vErrors === null) {
              vErrors = [err25];
            } else {
              vErrors.push(err25);
            }
            errors++;
          }
        }
        if (data3.severity !== void 0) {
          let data5 = data3.severity;
          if (typeof data5 !== "string") {
            const err26 = { instancePath: instancePath + "/finding/severity", schemaPath: "#/definitions/ReviewFinding/properties/severity/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err26];
            } else {
              vErrors.push(err26);
            }
            errors++;
          }
          if (!(data5 === "info" || data5 === "warning" || data5 === "blocker")) {
            const err27 = { instancePath: instancePath + "/finding/severity", schemaPath: "#/definitions/ReviewFinding/properties/severity/enum", keyword: "enum", params: { allowedValues: schema16.properties.severity.enum }, message: "must be equal to one of the allowed values" };
            if (vErrors === null) {
              vErrors = [err27];
            } else {
              vErrors.push(err27);
            }
            errors++;
          }
        }
        if (data3.finding !== void 0) {
          let data6 = data3.finding;
          if (typeof data6 === "string") {
            if (func2(data6) > 1e3) {
              const err28 = { instancePath: instancePath + "/finding/finding", schemaPath: "#/definitions/ReviewFinding/properties/finding/maxLength", keyword: "maxLength", params: { limit: 1e3 }, message: "must NOT have more than 1000 characters" };
              if (vErrors === null) {
                vErrors = [err28];
              } else {
                vErrors.push(err28);
              }
              errors++;
            }
            if (func2(data6) < 1) {
              const err29 = { instancePath: instancePath + "/finding/finding", schemaPath: "#/definitions/ReviewFinding/properties/finding/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
              if (vErrors === null) {
                vErrors = [err29];
              } else {
                vErrors.push(err29);
              }
              errors++;
            }
          } else {
            const err30 = { instancePath: instancePath + "/finding/finding", schemaPath: "#/definitions/ReviewFinding/properties/finding/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err30];
            } else {
              vErrors.push(err30);
            }
            errors++;
          }
        }
        if (data3.recommendation !== void 0) {
          let data7 = data3.recommendation;
          if (typeof data7 === "string") {
            if (func2(data7) > 1e3) {
              const err31 = { instancePath: instancePath + "/finding/recommendation", schemaPath: "#/definitions/ReviewFinding/properties/recommendation/maxLength", keyword: "maxLength", params: { limit: 1e3 }, message: "must NOT have more than 1000 characters" };
              if (vErrors === null) {
                vErrors = [err31];
              } else {
                vErrors.push(err31);
              }
              errors++;
            }
            if (func2(data7) < 1) {
              const err32 = { instancePath: instancePath + "/finding/recommendation", schemaPath: "#/definitions/ReviewFinding/properties/recommendation/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
              if (vErrors === null) {
                vErrors = [err32];
              } else {
                vErrors.push(err32);
              }
              errors++;
            }
          } else {
            const err33 = { instancePath: instancePath + "/finding/recommendation", schemaPath: "#/definitions/ReviewFinding/properties/recommendation/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err33];
            } else {
              vErrors.push(err33);
            }
            errors++;
          }
        }
        if (data3.sourceIds !== void 0) {
          let data8 = data3.sourceIds;
          if (Array.isArray(data8)) {
            if (data8.length > 6) {
              const err34 = { instancePath: instancePath + "/finding/sourceIds", schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/maxItems", keyword: "maxItems", params: { limit: 6 }, message: "must NOT have more than 6 items" };
              if (vErrors === null) {
                vErrors = [err34];
              } else {
                vErrors.push(err34);
              }
              errors++;
            }
            if (data8.length < 1) {
              const err35 = { instancePath: instancePath + "/finding/sourceIds", schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/minItems", keyword: "minItems", params: { limit: 1 }, message: "must NOT have fewer than 1 items" };
              if (vErrors === null) {
                vErrors = [err35];
              } else {
                vErrors.push(err35);
              }
              errors++;
            }
            const len0 = data8.length;
            for (let i0 = 0; i0 < len0; i0++) {
              let data9 = data8[i0];
              if (typeof data9 === "string") {
                if (func2(data9) > 128) {
                  const err36 = { instancePath: instancePath + "/finding/sourceIds/" + i0, schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/items/maxLength", keyword: "maxLength", params: { limit: 128 }, message: "must NOT have more than 128 characters" };
                  if (vErrors === null) {
                    vErrors = [err36];
                  } else {
                    vErrors.push(err36);
                  }
                  errors++;
                }
              } else {
                const err37 = { instancePath: instancePath + "/finding/sourceIds/" + i0, schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/items/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err37];
                } else {
                  vErrors.push(err37);
                }
                errors++;
              }
            }
            let i1 = data8.length;
            let j0;
            if (i1 > 1) {
              const indices0 = {};
              for (; i1--; ) {
                let item0 = data8[i1];
                if (typeof item0 !== "string") {
                  continue;
                }
                if (typeof indices0[item0] == "number") {
                  j0 = indices0[item0];
                  const err38 = { instancePath: instancePath + "/finding/sourceIds", schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/uniqueItems", keyword: "uniqueItems", params: { i: i1, j: j0 }, message: "must NOT have duplicate items (items ## " + j0 + " and " + i1 + " are identical)" };
                  if (vErrors === null) {
                    vErrors = [err38];
                  } else {
                    vErrors.push(err38);
                  }
                  errors++;
                  break;
                }
                indices0[item0] = i1;
              }
            }
          } else {
            const err39 = { instancePath: instancePath + "/finding/sourceIds", schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/type", keyword: "type", params: { type: "array" }, message: "must be array" };
            if (vErrors === null) {
              vErrors = [err39];
            } else {
              vErrors.push(err39);
            }
            errors++;
          }
        }
      } else {
        const err40 = { instancePath: instancePath + "/finding", schemaPath: "#/definitions/ReviewFinding/type", keyword: "type", params: { type: "object" }, message: "must be object" };
        if (vErrors === null) {
          vErrors = [err40];
        } else {
          vErrors.push(err40);
        }
        errors++;
      }
    }
    if (data.intent !== void 0) {
      let data10 = data.intent;
      if (typeof data10 !== "string") {
        const err41 = { instancePath: instancePath + "/intent", schemaPath: "#/definitions/DesignChange/properties/intent/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err41];
        } else {
          vErrors.push(err41);
        }
        errors++;
      }
      if (!(data10 === "recommendation" || data10 === "challenge")) {
        const err42 = { instancePath: instancePath + "/intent", schemaPath: "#/definitions/DesignChange/properties/intent/enum", keyword: "enum", params: { allowedValues: schema33.enum }, message: "must be equal to one of the allowed values" };
        if (vErrors === null) {
          vErrors = [err42];
        } else {
          vErrors.push(err42);
        }
        errors++;
      }
    }
    if (data.instruction !== void 0) {
      let data11 = data.instruction;
      if (typeof data11 === "string") {
        if (func2(data11) > 2e3) {
          const err43 = { instancePath: instancePath + "/instruction", schemaPath: "#/properties/instruction/maxLength", keyword: "maxLength", params: { limit: 2e3 }, message: "must NOT have more than 2000 characters" };
          if (vErrors === null) {
            vErrors = [err43];
          } else {
            vErrors.push(err43);
          }
          errors++;
        }
        if (func2(data11) < 10) {
          const err44 = { instancePath: instancePath + "/instruction", schemaPath: "#/properties/instruction/minLength", keyword: "minLength", params: { limit: 10 }, message: "must NOT have fewer than 10 characters" };
          if (vErrors === null) {
            vErrors = [err44];
          } else {
            vErrors.push(err44);
          }
          errors++;
        }
      } else {
        const err45 = { instancePath: instancePath + "/instruction", schemaPath: "#/properties/instruction/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err45];
        } else {
          vErrors.push(err45);
        }
        errors++;
      }
    }
    if (data.refinement !== void 0) {
      let data12 = data.refinement;
      if (typeof data12 === "string") {
        if (func2(data12) > 4e3) {
          const err46 = { instancePath: instancePath + "/refinement", schemaPath: "#/properties/refinement/maxLength", keyword: "maxLength", params: { limit: 4e3 }, message: "must NOT have more than 4000 characters" };
          if (vErrors === null) {
            vErrors = [err46];
          } else {
            vErrors.push(err46);
          }
          errors++;
        }
        if (func2(data12) < 10) {
          const err47 = { instancePath: instancePath + "/refinement", schemaPath: "#/properties/refinement/minLength", keyword: "minLength", params: { limit: 10 }, message: "must NOT have fewer than 10 characters" };
          if (vErrors === null) {
            vErrors = [err47];
          } else {
            vErrors.push(err47);
          }
          errors++;
        }
      } else {
        const err48 = { instancePath: instancePath + "/refinement", schemaPath: "#/properties/refinement/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err48];
        } else {
          vErrors.push(err48);
        }
        errors++;
      }
    }
    if (data.approvedAt !== void 0) {
      let data13 = data.approvedAt;
      if (typeof data13 === "string") {
        if (!formats0.validate(data13)) {
          const err49 = { instancePath: instancePath + "/approvedAt", schemaPath: "#/properties/approvedAt/format", keyword: "format", params: { format: "date-time" }, message: 'must match format "date-time"' };
          if (vErrors === null) {
            vErrors = [err49];
          } else {
            vErrors.push(err49);
          }
          errors++;
        }
      } else {
        const err50 = { instancePath: instancePath + "/approvedAt", schemaPath: "#/properties/approvedAt/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err50];
        } else {
          vErrors.push(err50);
        }
        errors++;
      }
    }
    if (data.actor !== void 0) {
      let data14 = data.actor;
      if (typeof data14 !== "string") {
        const err51 = { instancePath: instancePath + "/actor", schemaPath: "#/properties/actor/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err51];
        } else {
          vErrors.push(err51);
        }
        errors++;
      }
      if ("demo-human" !== data14) {
        const err52 = { instancePath: instancePath + "/actor", schemaPath: "#/properties/actor/const", keyword: "const", params: { allowedValue: "demo-human" }, message: "must be equal to constant" };
        if (vErrors === null) {
          vErrors = [err52];
        } else {
          vErrors.push(err52);
        }
        errors++;
      }
    }
    if (data.scope !== void 0) {
      let data15 = data.scope;
      if (typeof data15 !== "string") {
        const err53 = { instancePath: instancePath + "/scope", schemaPath: "#/properties/scope/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err53];
        } else {
          vErrors.push(err53);
        }
        errors++;
      }
      if ("design-revision-only" !== data15) {
        const err54 = { instancePath: instancePath + "/scope", schemaPath: "#/properties/scope/const", keyword: "const", params: { allowedValue: "design-revision-only" }, message: "must be equal to constant" };
        if (vErrors === null) {
          vErrors = [err54];
        } else {
          vErrors.push(err54);
        }
        errors++;
      }
    }
  } else {
    const err55 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err55];
    } else {
      vErrors.push(err55);
    }
    errors++;
  }
  validate26.errors = vErrors;
  return errors === 0;
}
function validate47(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.jobId === void 0) {
      const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "jobId" }, message: "must have required property 'jobId'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.status === void 0) {
      const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "status" }, message: "must have required property 'status'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    if (data.events === void 0) {
      const err2 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "events" }, message: "must have required property 'events'" };
      if (vErrors === null) {
        vErrors = [err2];
      } else {
        vErrors.push(err2);
      }
      errors++;
    }
    if (data.result === void 0) {
      const err3 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "result" }, message: "must have required property 'result'" };
      if (vErrors === null) {
        vErrors = [err3];
      } else {
        vErrors.push(err3);
      }
      errors++;
    }
    if (data.error === void 0) {
      const err4 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "error" }, message: "must have required property 'error'" };
      if (vErrors === null) {
        vErrors = [err4];
      } else {
        vErrors.push(err4);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!(key0 === "jobId" || key0 === "status" || key0 === "events" || key0 === "result" || key0 === "error" || key0 === "changeApproval")) {
        const err5 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err5];
        } else {
          vErrors.push(err5);
        }
        errors++;
      }
    }
    if (data.jobId !== void 0) {
      if (typeof data.jobId !== "string") {
        const err6 = { instancePath: instancePath + "/jobId", schemaPath: "#/properties/jobId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err6];
        } else {
          vErrors.push(err6);
        }
        errors++;
      }
    }
    if (data.status !== void 0) {
      let data1 = data.status;
      if (typeof data1 !== "string") {
        const err7 = { instancePath: instancePath + "/status", schemaPath: "#/properties/status/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err7];
        } else {
          vErrors.push(err7);
        }
        errors++;
      }
      if (!(data1 === "queued" || data1 === "running" || data1 === "succeeded" || data1 === "failed")) {
        const err8 = { instancePath: instancePath + "/status", schemaPath: "#/properties/status/enum", keyword: "enum", params: { allowedValues: schema25.properties.status.enum }, message: "must be equal to one of the allowed values" };
        if (vErrors === null) {
          vErrors = [err8];
        } else {
          vErrors.push(err8);
        }
        errors++;
      }
    }
    if (data.events !== void 0) {
      let data2 = data.events;
      if (Array.isArray(data2)) {
        const len0 = data2.length;
        for (let i0 = 0; i0 < len0; i0++) {
          let data3 = data2[i0];
          if (data3 && typeof data3 == "object" && !Array.isArray(data3)) {
            if (data3.sequence === void 0) {
              const err9 = { instancePath: instancePath + "/events/" + i0, schemaPath: "#/definitions/StudioEvent/required", keyword: "required", params: { missingProperty: "sequence" }, message: "must have required property 'sequence'" };
              if (vErrors === null) {
                vErrors = [err9];
              } else {
                vErrors.push(err9);
              }
              errors++;
            }
            if (data3.stage === void 0) {
              const err10 = { instancePath: instancePath + "/events/" + i0, schemaPath: "#/definitions/StudioEvent/required", keyword: "required", params: { missingProperty: "stage" }, message: "must have required property 'stage'" };
              if (vErrors === null) {
                vErrors = [err10];
              } else {
                vErrors.push(err10);
              }
              errors++;
            }
            if (data3.message === void 0) {
              const err11 = { instancePath: instancePath + "/events/" + i0, schemaPath: "#/definitions/StudioEvent/required", keyword: "required", params: { missingProperty: "message" }, message: "must have required property 'message'" };
              if (vErrors === null) {
                vErrors = [err11];
              } else {
                vErrors.push(err11);
              }
              errors++;
            }
            if (data3.at === void 0) {
              const err12 = { instancePath: instancePath + "/events/" + i0, schemaPath: "#/definitions/StudioEvent/required", keyword: "required", params: { missingProperty: "at" }, message: "must have required property 'at'" };
              if (vErrors === null) {
                vErrors = [err12];
              } else {
                vErrors.push(err12);
              }
              errors++;
            }
            for (const key1 in data3) {
              if (!(key1 === "sequence" || key1 === "stage" || key1 === "message" || key1 === "at")) {
                const err13 = { instancePath: instancePath + "/events/" + i0, schemaPath: "#/definitions/StudioEvent/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key1 }, message: "must NOT have additional properties" };
                if (vErrors === null) {
                  vErrors = [err13];
                } else {
                  vErrors.push(err13);
                }
                errors++;
              }
            }
            if (data3.sequence !== void 0) {
              let data4 = data3.sequence;
              if (!(typeof data4 == "number" && (!(data4 % 1) && !isNaN(data4)))) {
                const err14 = { instancePath: instancePath + "/events/" + i0 + "/sequence", schemaPath: "#/definitions/StudioEvent/properties/sequence/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                if (vErrors === null) {
                  vErrors = [err14];
                } else {
                  vErrors.push(err14);
                }
                errors++;
              }
              if (typeof data4 == "number") {
                if (data4 < 1 || isNaN(data4)) {
                  const err15 = { instancePath: instancePath + "/events/" + i0 + "/sequence", schemaPath: "#/definitions/StudioEvent/properties/sequence/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                  if (vErrors === null) {
                    vErrors = [err15];
                  } else {
                    vErrors.push(err15);
                  }
                  errors++;
                }
              }
            }
            if (data3.stage !== void 0) {
              let data5 = data3.stage;
              if (typeof data5 !== "string") {
                const err16 = { instancePath: instancePath + "/events/" + i0 + "/stage", schemaPath: "#/definitions/StudioEvent/properties/stage/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err16];
                } else {
                  vErrors.push(err16);
                }
                errors++;
              }
              if (!(data5 === "intake" || data5 === "synthesis" || data5 === "assurance" || data5 === "complete" || data5 === "error")) {
                const err17 = { instancePath: instancePath + "/events/" + i0 + "/stage", schemaPath: "#/definitions/StudioEvent/properties/stage/enum", keyword: "enum", params: { allowedValues: schema26.properties.stage.enum }, message: "must be equal to one of the allowed values" };
                if (vErrors === null) {
                  vErrors = [err17];
                } else {
                  vErrors.push(err17);
                }
                errors++;
              }
            }
            if (data3.message !== void 0) {
              if (typeof data3.message !== "string") {
                const err18 = { instancePath: instancePath + "/events/" + i0 + "/message", schemaPath: "#/definitions/StudioEvent/properties/message/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err18];
                } else {
                  vErrors.push(err18);
                }
                errors++;
              }
            }
            if (data3.at !== void 0) {
              if (typeof data3.at !== "string") {
                const err19 = { instancePath: instancePath + "/events/" + i0 + "/at", schemaPath: "#/definitions/StudioEvent/properties/at/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err19];
                } else {
                  vErrors.push(err19);
                }
                errors++;
              }
            }
          } else {
            const err20 = { instancePath: instancePath + "/events/" + i0, schemaPath: "#/definitions/StudioEvent/type", keyword: "type", params: { type: "object" }, message: "must be object" };
            if (vErrors === null) {
              vErrors = [err20];
            } else {
              vErrors.push(err20);
            }
            errors++;
          }
        }
      } else {
        const err21 = { instancePath: instancePath + "/events", schemaPath: "#/properties/events/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err21];
        } else {
          vErrors.push(err21);
        }
        errors++;
      }
    }
    if (data.result !== void 0) {
      let data8 = data.result;
      const _errs21 = errors;
      let valid5 = false;
      const _errs22 = errors;
      if (!validate23(data8, { instancePath: instancePath + "/result", parentData: data, parentDataProperty: "result", rootData })) {
        vErrors = vErrors === null ? validate23.errors : vErrors.concat(validate23.errors);
        errors = vErrors.length;
      }
      var _valid0 = _errs22 === errors;
      valid5 = valid5 || _valid0;
      if (!valid5) {
        const _errs23 = errors;
        if (data8 !== null) {
          const err22 = { instancePath: instancePath + "/result", schemaPath: "#/properties/result/anyOf/1/type", keyword: "type", params: { type: "null" }, message: "must be null" };
          if (vErrors === null) {
            vErrors = [err22];
          } else {
            vErrors.push(err22);
          }
          errors++;
        }
        var _valid0 = _errs23 === errors;
        valid5 = valid5 || _valid0;
      }
      if (!valid5) {
        const err23 = { instancePath: instancePath + "/result", schemaPath: "#/properties/result/anyOf", keyword: "anyOf", params: {}, message: "must match a schema in anyOf" };
        if (vErrors === null) {
          vErrors = [err23];
        } else {
          vErrors.push(err23);
        }
        errors++;
      } else {
        errors = _errs21;
        if (vErrors !== null) {
          if (_errs21) {
            vErrors.length = _errs21;
          } else {
            vErrors = null;
          }
        }
      }
    }
    if (data.error !== void 0) {
      let data9 = data.error;
      const _errs26 = errors;
      let valid6 = false;
      const _errs27 = errors;
      if (data9 && typeof data9 == "object" && !Array.isArray(data9)) {
        if (data9.code === void 0) {
          const err24 = { instancePath: instancePath + "/error", schemaPath: "#/definitions/StudioError/required", keyword: "required", params: { missingProperty: "code" }, message: "must have required property 'code'" };
          if (vErrors === null) {
            vErrors = [err24];
          } else {
            vErrors.push(err24);
          }
          errors++;
        }
        if (data9.message === void 0) {
          const err25 = { instancePath: instancePath + "/error", schemaPath: "#/definitions/StudioError/required", keyword: "required", params: { missingProperty: "message" }, message: "must have required property 'message'" };
          if (vErrors === null) {
            vErrors = [err25];
          } else {
            vErrors.push(err25);
          }
          errors++;
        }
        if (data9.retryable === void 0) {
          const err26 = { instancePath: instancePath + "/error", schemaPath: "#/definitions/StudioError/required", keyword: "required", params: { missingProperty: "retryable" }, message: "must have required property 'retryable'" };
          if (vErrors === null) {
            vErrors = [err26];
          } else {
            vErrors.push(err26);
          }
          errors++;
        }
        for (const key2 in data9) {
          if (!(key2 === "code" || key2 === "message" || key2 === "retryable")) {
            const err27 = { instancePath: instancePath + "/error", schemaPath: "#/definitions/StudioError/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key2 }, message: "must NOT have additional properties" };
            if (vErrors === null) {
              vErrors = [err27];
            } else {
              vErrors.push(err27);
            }
            errors++;
          }
        }
        if (data9.code !== void 0) {
          if (typeof data9.code !== "string") {
            const err28 = { instancePath: instancePath + "/error/code", schemaPath: "#/definitions/StudioError/properties/code/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err28];
            } else {
              vErrors.push(err28);
            }
            errors++;
          }
        }
        if (data9.message !== void 0) {
          if (typeof data9.message !== "string") {
            const err29 = { instancePath: instancePath + "/error/message", schemaPath: "#/definitions/StudioError/properties/message/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err29];
            } else {
              vErrors.push(err29);
            }
            errors++;
          }
        }
        if (data9.retryable !== void 0) {
          if (typeof data9.retryable !== "boolean") {
            const err30 = { instancePath: instancePath + "/error/retryable", schemaPath: "#/definitions/StudioError/properties/retryable/type", keyword: "type", params: { type: "boolean" }, message: "must be boolean" };
            if (vErrors === null) {
              vErrors = [err30];
            } else {
              vErrors.push(err30);
            }
            errors++;
          }
        }
      } else {
        const err31 = { instancePath: instancePath + "/error", schemaPath: "#/definitions/StudioError/type", keyword: "type", params: { type: "object" }, message: "must be object" };
        if (vErrors === null) {
          vErrors = [err31];
        } else {
          vErrors.push(err31);
        }
        errors++;
      }
      var _valid1 = _errs27 === errors;
      valid6 = valid6 || _valid1;
      if (!valid6) {
        const _errs37 = errors;
        if (data9 !== null) {
          const err32 = { instancePath: instancePath + "/error", schemaPath: "#/properties/error/anyOf/1/type", keyword: "type", params: { type: "null" }, message: "must be null" };
          if (vErrors === null) {
            vErrors = [err32];
          } else {
            vErrors.push(err32);
          }
          errors++;
        }
        var _valid1 = _errs37 === errors;
        valid6 = valid6 || _valid1;
      }
      if (!valid6) {
        const err33 = { instancePath: instancePath + "/error", schemaPath: "#/properties/error/anyOf", keyword: "anyOf", params: {}, message: "must match a schema in anyOf" };
        if (vErrors === null) {
          vErrors = [err33];
        } else {
          vErrors.push(err33);
        }
        errors++;
      } else {
        errors = _errs26;
        if (vErrors !== null) {
          if (_errs26) {
            vErrors.length = _errs26;
          } else {
            vErrors = null;
          }
        }
      }
    }
    if (data.changeApproval !== void 0) {
      if (!validate26(data.changeApproval, { instancePath: instancePath + "/changeApproval", parentData: data, parentDataProperty: "changeApproval", rootData })) {
        vErrors = vErrors === null ? validate26.errors : vErrors.concat(validate26.errors);
        errors = vErrors.length;
      }
    }
  } else {
    const err34 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err34];
    } else {
      vErrors.push(err34);
    }
    errors++;
  }
  validate47.errors = vErrors;
  return errors === 0;
}
function validate10(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  ;
  let vErrors = null;
  let errors = 0;
  if (!validate47(data, { instancePath, parentData, parentDataProperty, rootData })) {
    vErrors = vErrors === null ? validate47.errors : vErrors.concat(validate47.errors);
    errors = vErrors.length;
  }
  validate10.errors = vErrors;
  return errors === 0;
}
var buildShape = validate51;
var schema35 = { "type": "object", "additionalProperties": false, "properties": { "buildId": { "type": "string" }, "resultId": { "type": "string" }, "optionId": { "type": "string" }, "status": { "type": "string", "enum": ["compiled", "failed", "blocked"] }, "compilerVersion": { "type": ["string", "null"] }, "exitCode": { "type": ["integer", "null"] }, "diagnostics": { "type": "string" }, "files": { "type": "array", "items": { "$ref": "#/definitions/BuildFile" } }, "downloadUrl": { "type": ["string", "null"] }, "limitations": { "type": "array", "items": { "type": "string" } }, "deploymentStatus": { "type": "string", "const": "not-deployed" } }, "required": ["buildId", "resultId", "optionId", "status", "compilerVersion", "exitCode", "diagnostics", "files", "downloadUrl", "limitations", "deploymentStatus"] };
function validate52(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.buildId === void 0) {
      const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "buildId" }, message: "must have required property 'buildId'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.resultId === void 0) {
      const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "resultId" }, message: "must have required property 'resultId'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    if (data.optionId === void 0) {
      const err2 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "optionId" }, message: "must have required property 'optionId'" };
      if (vErrors === null) {
        vErrors = [err2];
      } else {
        vErrors.push(err2);
      }
      errors++;
    }
    if (data.status === void 0) {
      const err3 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "status" }, message: "must have required property 'status'" };
      if (vErrors === null) {
        vErrors = [err3];
      } else {
        vErrors.push(err3);
      }
      errors++;
    }
    if (data.compilerVersion === void 0) {
      const err4 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "compilerVersion" }, message: "must have required property 'compilerVersion'" };
      if (vErrors === null) {
        vErrors = [err4];
      } else {
        vErrors.push(err4);
      }
      errors++;
    }
    if (data.exitCode === void 0) {
      const err5 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "exitCode" }, message: "must have required property 'exitCode'" };
      if (vErrors === null) {
        vErrors = [err5];
      } else {
        vErrors.push(err5);
      }
      errors++;
    }
    if (data.diagnostics === void 0) {
      const err6 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "diagnostics" }, message: "must have required property 'diagnostics'" };
      if (vErrors === null) {
        vErrors = [err6];
      } else {
        vErrors.push(err6);
      }
      errors++;
    }
    if (data.files === void 0) {
      const err7 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "files" }, message: "must have required property 'files'" };
      if (vErrors === null) {
        vErrors = [err7];
      } else {
        vErrors.push(err7);
      }
      errors++;
    }
    if (data.downloadUrl === void 0) {
      const err8 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "downloadUrl" }, message: "must have required property 'downloadUrl'" };
      if (vErrors === null) {
        vErrors = [err8];
      } else {
        vErrors.push(err8);
      }
      errors++;
    }
    if (data.limitations === void 0) {
      const err9 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "limitations" }, message: "must have required property 'limitations'" };
      if (vErrors === null) {
        vErrors = [err9];
      } else {
        vErrors.push(err9);
      }
      errors++;
    }
    if (data.deploymentStatus === void 0) {
      const err10 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "deploymentStatus" }, message: "must have required property 'deploymentStatus'" };
      if (vErrors === null) {
        vErrors = [err10];
      } else {
        vErrors.push(err10);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!func24.call(schema35.properties, key0)) {
        const err11 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err11];
        } else {
          vErrors.push(err11);
        }
        errors++;
      }
    }
    if (data.buildId !== void 0) {
      if (typeof data.buildId !== "string") {
        const err12 = { instancePath: instancePath + "/buildId", schemaPath: "#/properties/buildId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err12];
        } else {
          vErrors.push(err12);
        }
        errors++;
      }
    }
    if (data.resultId !== void 0) {
      if (typeof data.resultId !== "string") {
        const err13 = { instancePath: instancePath + "/resultId", schemaPath: "#/properties/resultId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err13];
        } else {
          vErrors.push(err13);
        }
        errors++;
      }
    }
    if (data.optionId !== void 0) {
      if (typeof data.optionId !== "string") {
        const err14 = { instancePath: instancePath + "/optionId", schemaPath: "#/properties/optionId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err14];
        } else {
          vErrors.push(err14);
        }
        errors++;
      }
    }
    if (data.status !== void 0) {
      let data3 = data.status;
      if (typeof data3 !== "string") {
        const err15 = { instancePath: instancePath + "/status", schemaPath: "#/properties/status/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err15];
        } else {
          vErrors.push(err15);
        }
        errors++;
      }
      if (!(data3 === "compiled" || data3 === "failed" || data3 === "blocked")) {
        const err16 = { instancePath: instancePath + "/status", schemaPath: "#/properties/status/enum", keyword: "enum", params: { allowedValues: schema35.properties.status.enum }, message: "must be equal to one of the allowed values" };
        if (vErrors === null) {
          vErrors = [err16];
        } else {
          vErrors.push(err16);
        }
        errors++;
      }
    }
    if (data.compilerVersion !== void 0) {
      let data4 = data.compilerVersion;
      if (typeof data4 !== "string" && data4 !== null) {
        const err17 = { instancePath: instancePath + "/compilerVersion", schemaPath: "#/properties/compilerVersion/type", keyword: "type", params: { type: schema35.properties.compilerVersion.type }, message: "must be string,null" };
        if (vErrors === null) {
          vErrors = [err17];
        } else {
          vErrors.push(err17);
        }
        errors++;
      }
    }
    if (data.exitCode !== void 0) {
      let data5 = data.exitCode;
      if (!(typeof data5 == "number" && (!(data5 % 1) && !isNaN(data5))) && data5 !== null) {
        const err18 = { instancePath: instancePath + "/exitCode", schemaPath: "#/properties/exitCode/type", keyword: "type", params: { type: schema35.properties.exitCode.type }, message: "must be integer,null" };
        if (vErrors === null) {
          vErrors = [err18];
        } else {
          vErrors.push(err18);
        }
        errors++;
      }
    }
    if (data.diagnostics !== void 0) {
      if (typeof data.diagnostics !== "string") {
        const err19 = { instancePath: instancePath + "/diagnostics", schemaPath: "#/properties/diagnostics/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err19];
        } else {
          vErrors.push(err19);
        }
        errors++;
      }
    }
    if (data.files !== void 0) {
      let data7 = data.files;
      if (Array.isArray(data7)) {
        const len0 = data7.length;
        for (let i0 = 0; i0 < len0; i0++) {
          let data8 = data7[i0];
          if (data8 && typeof data8 == "object" && !Array.isArray(data8)) {
            if (data8.path === void 0) {
              const err20 = { instancePath: instancePath + "/files/" + i0, schemaPath: "#/definitions/BuildFile/required", keyword: "required", params: { missingProperty: "path" }, message: "must have required property 'path'" };
              if (vErrors === null) {
                vErrors = [err20];
              } else {
                vErrors.push(err20);
              }
              errors++;
            }
            if (data8.content === void 0) {
              const err21 = { instancePath: instancePath + "/files/" + i0, schemaPath: "#/definitions/BuildFile/required", keyword: "required", params: { missingProperty: "content" }, message: "must have required property 'content'" };
              if (vErrors === null) {
                vErrors = [err21];
              } else {
                vErrors.push(err21);
              }
              errors++;
            }
            if (data8.sha256 === void 0) {
              const err22 = { instancePath: instancePath + "/files/" + i0, schemaPath: "#/definitions/BuildFile/required", keyword: "required", params: { missingProperty: "sha256" }, message: "must have required property 'sha256'" };
              if (vErrors === null) {
                vErrors = [err22];
              } else {
                vErrors.push(err22);
              }
              errors++;
            }
            for (const key1 in data8) {
              if (!(key1 === "path" || key1 === "content" || key1 === "sha256")) {
                const err23 = { instancePath: instancePath + "/files/" + i0, schemaPath: "#/definitions/BuildFile/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key1 }, message: "must NOT have additional properties" };
                if (vErrors === null) {
                  vErrors = [err23];
                } else {
                  vErrors.push(err23);
                }
                errors++;
              }
            }
            if (data8.path !== void 0) {
              if (typeof data8.path !== "string") {
                const err24 = { instancePath: instancePath + "/files/" + i0 + "/path", schemaPath: "#/definitions/BuildFile/properties/path/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err24];
                } else {
                  vErrors.push(err24);
                }
                errors++;
              }
            }
            if (data8.content !== void 0) {
              if (typeof data8.content !== "string") {
                const err25 = { instancePath: instancePath + "/files/" + i0 + "/content", schemaPath: "#/definitions/BuildFile/properties/content/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err25];
                } else {
                  vErrors.push(err25);
                }
                errors++;
              }
            }
            if (data8.sha256 !== void 0) {
              if (typeof data8.sha256 !== "string") {
                const err26 = { instancePath: instancePath + "/files/" + i0 + "/sha256", schemaPath: "#/definitions/BuildFile/properties/sha256/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err26];
                } else {
                  vErrors.push(err26);
                }
                errors++;
              }
            }
          } else {
            const err27 = { instancePath: instancePath + "/files/" + i0, schemaPath: "#/definitions/BuildFile/type", keyword: "type", params: { type: "object" }, message: "must be object" };
            if (vErrors === null) {
              vErrors = [err27];
            } else {
              vErrors.push(err27);
            }
            errors++;
          }
        }
      } else {
        const err28 = { instancePath: instancePath + "/files", schemaPath: "#/properties/files/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err28];
        } else {
          vErrors.push(err28);
        }
        errors++;
      }
    }
    if (data.downloadUrl !== void 0) {
      let data12 = data.downloadUrl;
      if (typeof data12 !== "string" && data12 !== null) {
        const err29 = { instancePath: instancePath + "/downloadUrl", schemaPath: "#/properties/downloadUrl/type", keyword: "type", params: { type: schema35.properties.downloadUrl.type }, message: "must be string,null" };
        if (vErrors === null) {
          vErrors = [err29];
        } else {
          vErrors.push(err29);
        }
        errors++;
      }
    }
    if (data.limitations !== void 0) {
      let data13 = data.limitations;
      if (Array.isArray(data13)) {
        const len1 = data13.length;
        for (let i1 = 0; i1 < len1; i1++) {
          if (typeof data13[i1] !== "string") {
            const err30 = { instancePath: instancePath + "/limitations/" + i1, schemaPath: "#/properties/limitations/items/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err30];
            } else {
              vErrors.push(err30);
            }
            errors++;
          }
        }
      } else {
        const err31 = { instancePath: instancePath + "/limitations", schemaPath: "#/properties/limitations/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err31];
        } else {
          vErrors.push(err31);
        }
        errors++;
      }
    }
    if (data.deploymentStatus !== void 0) {
      let data15 = data.deploymentStatus;
      if (typeof data15 !== "string") {
        const err32 = { instancePath: instancePath + "/deploymentStatus", schemaPath: "#/properties/deploymentStatus/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err32];
        } else {
          vErrors.push(err32);
        }
        errors++;
      }
      if ("not-deployed" !== data15) {
        const err33 = { instancePath: instancePath + "/deploymentStatus", schemaPath: "#/properties/deploymentStatus/const", keyword: "const", params: { allowedValue: "not-deployed" }, message: "must be equal to constant" };
        if (vErrors === null) {
          vErrors = [err33];
        } else {
          vErrors.push(err33);
        }
        errors++;
      }
    }
  } else {
    const err34 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err34];
    } else {
      vErrors.push(err34);
    }
    errors++;
  }
  validate52.errors = vErrors;
  return errors === 0;
}
function validate51(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  ;
  let vErrors = null;
  let errors = 0;
  if (!validate52(data, { instancePath, parentData, parentDataProperty, rootData })) {
    vErrors = vErrors === null ? validate52.errors : vErrors.concat(validate52.errors);
    errors = vErrors.length;
  }
  validate51.errors = vErrors;
  return errors === 0;
}
var inputShape = validate54;
var schema13 = { "type": "object", "additionalProperties": false, "properties": { "title": { "type": "string", "maxLength": 160 }, "prompt": { "type": "string", "minLength": 10, "maxLength": 12e3 }, "documents": { "type": "array", "maxItems": 5, "items": { "$ref": "#/definitions/SourceDocument" } }, "refinement": { "type": "string", "maxLength": 4e3 }, "previousResultId": { "type": ["string", "null"], "maxLength": 80 }, "idempotencyKey": { "type": "string", "minLength": 8, "maxLength": 128 }, "consentToModel": { "type": "boolean", "const": true }, "designChange": { "$ref": "#/definitions/DesignChange" } }, "required": ["title", "prompt", "documents", "refinement", "previousResultId", "idempotencyKey", "consentToModel"], "allOf": [{ "if": { "required": ["designChange"] }, "then": { "properties": { "refinement": { "type": "string", "minLength": 10, "maxLength": 2e3 }, "previousResultId": { "type": "string", "minLength": 1, "maxLength": 80 } } } }] };
var schema15 = { "type": "object", "additionalProperties": false, "description": "Explicit permission to revise a particular stored design finding, never risk acceptance.", "properties": { "optionId": { "type": "string", "pattern": "^[a-z][a-z0-9-]{0,39}$" }, "finding": { "$ref": "#/definitions/ReviewFinding" }, "intent": { "type": "string", "enum": ["recommendation", "challenge"] }, "confirmRevision": { "type": "boolean", "const": true } }, "required": ["optionId", "finding", "intent", "confirmRevision"] };
function validate13(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.optionId === void 0) {
      const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "optionId" }, message: "must have required property 'optionId'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.finding === void 0) {
      const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "finding" }, message: "must have required property 'finding'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    if (data.intent === void 0) {
      const err2 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "intent" }, message: "must have required property 'intent'" };
      if (vErrors === null) {
        vErrors = [err2];
      } else {
        vErrors.push(err2);
      }
      errors++;
    }
    if (data.confirmRevision === void 0) {
      const err3 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "confirmRevision" }, message: "must have required property 'confirmRevision'" };
      if (vErrors === null) {
        vErrors = [err3];
      } else {
        vErrors.push(err3);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!(key0 === "optionId" || key0 === "finding" || key0 === "intent" || key0 === "confirmRevision")) {
        const err4 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err4];
        } else {
          vErrors.push(err4);
        }
        errors++;
      }
    }
    if (data.optionId !== void 0) {
      let data0 = data.optionId;
      if (typeof data0 === "string") {
        if (!pattern0.test(data0)) {
          const err5 = { instancePath: instancePath + "/optionId", schemaPath: "#/properties/optionId/pattern", keyword: "pattern", params: { pattern: "^[a-z][a-z0-9-]{0,39}$" }, message: 'must match pattern "^[a-z][a-z0-9-]{0,39}$"' };
          if (vErrors === null) {
            vErrors = [err5];
          } else {
            vErrors.push(err5);
          }
          errors++;
        }
      } else {
        const err6 = { instancePath: instancePath + "/optionId", schemaPath: "#/properties/optionId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err6];
        } else {
          vErrors.push(err6);
        }
        errors++;
      }
    }
    if (data.finding !== void 0) {
      let data1 = data.finding;
      if (data1 && typeof data1 == "object" && !Array.isArray(data1)) {
        if (data1.dimension === void 0) {
          const err7 = { instancePath: instancePath + "/finding", schemaPath: "#/definitions/ReviewFinding/required", keyword: "required", params: { missingProperty: "dimension" }, message: "must have required property 'dimension'" };
          if (vErrors === null) {
            vErrors = [err7];
          } else {
            vErrors.push(err7);
          }
          errors++;
        }
        if (data1.severity === void 0) {
          const err8 = { instancePath: instancePath + "/finding", schemaPath: "#/definitions/ReviewFinding/required", keyword: "required", params: { missingProperty: "severity" }, message: "must have required property 'severity'" };
          if (vErrors === null) {
            vErrors = [err8];
          } else {
            vErrors.push(err8);
          }
          errors++;
        }
        if (data1.finding === void 0) {
          const err9 = { instancePath: instancePath + "/finding", schemaPath: "#/definitions/ReviewFinding/required", keyword: "required", params: { missingProperty: "finding" }, message: "must have required property 'finding'" };
          if (vErrors === null) {
            vErrors = [err9];
          } else {
            vErrors.push(err9);
          }
          errors++;
        }
        if (data1.recommendation === void 0) {
          const err10 = { instancePath: instancePath + "/finding", schemaPath: "#/definitions/ReviewFinding/required", keyword: "required", params: { missingProperty: "recommendation" }, message: "must have required property 'recommendation'" };
          if (vErrors === null) {
            vErrors = [err10];
          } else {
            vErrors.push(err10);
          }
          errors++;
        }
        if (data1.sourceIds === void 0) {
          const err11 = { instancePath: instancePath + "/finding", schemaPath: "#/definitions/ReviewFinding/required", keyword: "required", params: { missingProperty: "sourceIds" }, message: "must have required property 'sourceIds'" };
          if (vErrors === null) {
            vErrors = [err11];
          } else {
            vErrors.push(err11);
          }
          errors++;
        }
        for (const key1 in data1) {
          if (!(key1 === "dimension" || key1 === "severity" || key1 === "finding" || key1 === "recommendation" || key1 === "sourceIds")) {
            const err12 = { instancePath: instancePath + "/finding", schemaPath: "#/definitions/ReviewFinding/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key1 }, message: "must NOT have additional properties" };
            if (vErrors === null) {
              vErrors = [err12];
            } else {
              vErrors.push(err12);
            }
            errors++;
          }
        }
        if (data1.dimension !== void 0) {
          let data2 = data1.dimension;
          if (typeof data2 !== "string") {
            const err13 = { instancePath: instancePath + "/finding/dimension", schemaPath: "#/definitions/ReviewFinding/properties/dimension/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err13];
            } else {
              vErrors.push(err13);
            }
            errors++;
          }
          if (!(data2 === "business" || data2 === "security" || data2 === "reliability" || data2 === "performance" || data2 === "cost" || data2 === "integration" || data2 === "compliance" || data2 === "operations" || data2 === "delivery")) {
            const err14 = { instancePath: instancePath + "/finding/dimension", schemaPath: "#/definitions/ReviewFinding/properties/dimension/enum", keyword: "enum", params: { allowedValues: schema16.properties.dimension.enum }, message: "must be equal to one of the allowed values" };
            if (vErrors === null) {
              vErrors = [err14];
            } else {
              vErrors.push(err14);
            }
            errors++;
          }
        }
        if (data1.severity !== void 0) {
          let data3 = data1.severity;
          if (typeof data3 !== "string") {
            const err15 = { instancePath: instancePath + "/finding/severity", schemaPath: "#/definitions/ReviewFinding/properties/severity/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err15];
            } else {
              vErrors.push(err15);
            }
            errors++;
          }
          if (!(data3 === "info" || data3 === "warning" || data3 === "blocker")) {
            const err16 = { instancePath: instancePath + "/finding/severity", schemaPath: "#/definitions/ReviewFinding/properties/severity/enum", keyword: "enum", params: { allowedValues: schema16.properties.severity.enum }, message: "must be equal to one of the allowed values" };
            if (vErrors === null) {
              vErrors = [err16];
            } else {
              vErrors.push(err16);
            }
            errors++;
          }
        }
        if (data1.finding !== void 0) {
          let data4 = data1.finding;
          if (typeof data4 === "string") {
            if (func2(data4) > 1e3) {
              const err17 = { instancePath: instancePath + "/finding/finding", schemaPath: "#/definitions/ReviewFinding/properties/finding/maxLength", keyword: "maxLength", params: { limit: 1e3 }, message: "must NOT have more than 1000 characters" };
              if (vErrors === null) {
                vErrors = [err17];
              } else {
                vErrors.push(err17);
              }
              errors++;
            }
            if (func2(data4) < 1) {
              const err18 = { instancePath: instancePath + "/finding/finding", schemaPath: "#/definitions/ReviewFinding/properties/finding/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
              if (vErrors === null) {
                vErrors = [err18];
              } else {
                vErrors.push(err18);
              }
              errors++;
            }
          } else {
            const err19 = { instancePath: instancePath + "/finding/finding", schemaPath: "#/definitions/ReviewFinding/properties/finding/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err19];
            } else {
              vErrors.push(err19);
            }
            errors++;
          }
        }
        if (data1.recommendation !== void 0) {
          let data5 = data1.recommendation;
          if (typeof data5 === "string") {
            if (func2(data5) > 1e3) {
              const err20 = { instancePath: instancePath + "/finding/recommendation", schemaPath: "#/definitions/ReviewFinding/properties/recommendation/maxLength", keyword: "maxLength", params: { limit: 1e3 }, message: "must NOT have more than 1000 characters" };
              if (vErrors === null) {
                vErrors = [err20];
              } else {
                vErrors.push(err20);
              }
              errors++;
            }
            if (func2(data5) < 1) {
              const err21 = { instancePath: instancePath + "/finding/recommendation", schemaPath: "#/definitions/ReviewFinding/properties/recommendation/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
              if (vErrors === null) {
                vErrors = [err21];
              } else {
                vErrors.push(err21);
              }
              errors++;
            }
          } else {
            const err22 = { instancePath: instancePath + "/finding/recommendation", schemaPath: "#/definitions/ReviewFinding/properties/recommendation/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err22];
            } else {
              vErrors.push(err22);
            }
            errors++;
          }
        }
        if (data1.sourceIds !== void 0) {
          let data6 = data1.sourceIds;
          if (Array.isArray(data6)) {
            if (data6.length > 6) {
              const err23 = { instancePath: instancePath + "/finding/sourceIds", schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/maxItems", keyword: "maxItems", params: { limit: 6 }, message: "must NOT have more than 6 items" };
              if (vErrors === null) {
                vErrors = [err23];
              } else {
                vErrors.push(err23);
              }
              errors++;
            }
            if (data6.length < 1) {
              const err24 = { instancePath: instancePath + "/finding/sourceIds", schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/minItems", keyword: "minItems", params: { limit: 1 }, message: "must NOT have fewer than 1 items" };
              if (vErrors === null) {
                vErrors = [err24];
              } else {
                vErrors.push(err24);
              }
              errors++;
            }
            const len0 = data6.length;
            for (let i0 = 0; i0 < len0; i0++) {
              let data7 = data6[i0];
              if (typeof data7 === "string") {
                if (func2(data7) > 128) {
                  const err25 = { instancePath: instancePath + "/finding/sourceIds/" + i0, schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/items/maxLength", keyword: "maxLength", params: { limit: 128 }, message: "must NOT have more than 128 characters" };
                  if (vErrors === null) {
                    vErrors = [err25];
                  } else {
                    vErrors.push(err25);
                  }
                  errors++;
                }
              } else {
                const err26 = { instancePath: instancePath + "/finding/sourceIds/" + i0, schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/items/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err26];
                } else {
                  vErrors.push(err26);
                }
                errors++;
              }
            }
            let i1 = data6.length;
            let j0;
            if (i1 > 1) {
              const indices0 = {};
              for (; i1--; ) {
                let item0 = data6[i1];
                if (typeof item0 !== "string") {
                  continue;
                }
                if (typeof indices0[item0] == "number") {
                  j0 = indices0[item0];
                  const err27 = { instancePath: instancePath + "/finding/sourceIds", schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/uniqueItems", keyword: "uniqueItems", params: { i: i1, j: j0 }, message: "must NOT have duplicate items (items ## " + j0 + " and " + i1 + " are identical)" };
                  if (vErrors === null) {
                    vErrors = [err27];
                  } else {
                    vErrors.push(err27);
                  }
                  errors++;
                  break;
                }
                indices0[item0] = i1;
              }
            }
          } else {
            const err28 = { instancePath: instancePath + "/finding/sourceIds", schemaPath: "#/definitions/ReviewFinding/properties/sourceIds/type", keyword: "type", params: { type: "array" }, message: "must be array" };
            if (vErrors === null) {
              vErrors = [err28];
            } else {
              vErrors.push(err28);
            }
            errors++;
          }
        }
      } else {
        const err29 = { instancePath: instancePath + "/finding", schemaPath: "#/definitions/ReviewFinding/type", keyword: "type", params: { type: "object" }, message: "must be object" };
        if (vErrors === null) {
          vErrors = [err29];
        } else {
          vErrors.push(err29);
        }
        errors++;
      }
    }
    if (data.intent !== void 0) {
      let data8 = data.intent;
      if (typeof data8 !== "string") {
        const err30 = { instancePath: instancePath + "/intent", schemaPath: "#/properties/intent/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err30];
        } else {
          vErrors.push(err30);
        }
        errors++;
      }
      if (!(data8 === "recommendation" || data8 === "challenge")) {
        const err31 = { instancePath: instancePath + "/intent", schemaPath: "#/properties/intent/enum", keyword: "enum", params: { allowedValues: schema15.properties.intent.enum }, message: "must be equal to one of the allowed values" };
        if (vErrors === null) {
          vErrors = [err31];
        } else {
          vErrors.push(err31);
        }
        errors++;
      }
    }
    if (data.confirmRevision !== void 0) {
      let data9 = data.confirmRevision;
      if (typeof data9 !== "boolean") {
        const err32 = { instancePath: instancePath + "/confirmRevision", schemaPath: "#/properties/confirmRevision/type", keyword: "type", params: { type: "boolean" }, message: "must be boolean" };
        if (vErrors === null) {
          vErrors = [err32];
        } else {
          vErrors.push(err32);
        }
        errors++;
      }
      if (true !== data9) {
        const err33 = { instancePath: instancePath + "/confirmRevision", schemaPath: "#/properties/confirmRevision/const", keyword: "const", params: { allowedValue: true }, message: "must be equal to constant" };
        if (vErrors === null) {
          vErrors = [err33];
        } else {
          vErrors.push(err33);
        }
        errors++;
      }
    }
  } else {
    const err34 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err34];
    } else {
      vErrors.push(err34);
    }
    errors++;
  }
  validate13.errors = vErrors;
  return errors === 0;
}
function validate55(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  const _errs2 = errors;
  let valid1 = true;
  const _errs3 = errors;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    let missing0;
    if (data.designChange === void 0 && (missing0 = "designChange")) {
      const err0 = {};
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
  }
  var _valid0 = _errs3 === errors;
  errors = _errs2;
  if (vErrors !== null) {
    if (_errs2) {
      vErrors.length = _errs2;
    } else {
      vErrors = null;
    }
  }
  if (_valid0) {
    const _errs4 = errors;
    if (data && typeof data == "object" && !Array.isArray(data)) {
      if (data.refinement !== void 0) {
        let data0 = data.refinement;
        if (typeof data0 === "string") {
          if (func2(data0) > 2e3) {
            const err1 = { instancePath: instancePath + "/refinement", schemaPath: "#/allOf/0/then/properties/refinement/maxLength", keyword: "maxLength", params: { limit: 2e3 }, message: "must NOT have more than 2000 characters" };
            if (vErrors === null) {
              vErrors = [err1];
            } else {
              vErrors.push(err1);
            }
            errors++;
          }
          if (func2(data0) < 10) {
            const err2 = { instancePath: instancePath + "/refinement", schemaPath: "#/allOf/0/then/properties/refinement/minLength", keyword: "minLength", params: { limit: 10 }, message: "must NOT have fewer than 10 characters" };
            if (vErrors === null) {
              vErrors = [err2];
            } else {
              vErrors.push(err2);
            }
            errors++;
          }
        } else {
          const err3 = { instancePath: instancePath + "/refinement", schemaPath: "#/allOf/0/then/properties/refinement/type", keyword: "type", params: { type: "string" }, message: "must be string" };
          if (vErrors === null) {
            vErrors = [err3];
          } else {
            vErrors.push(err3);
          }
          errors++;
        }
      }
      if (data.previousResultId !== void 0) {
        let data1 = data.previousResultId;
        if (typeof data1 === "string") {
          if (func2(data1) > 80) {
            const err4 = { instancePath: instancePath + "/previousResultId", schemaPath: "#/allOf/0/then/properties/previousResultId/maxLength", keyword: "maxLength", params: { limit: 80 }, message: "must NOT have more than 80 characters" };
            if (vErrors === null) {
              vErrors = [err4];
            } else {
              vErrors.push(err4);
            }
            errors++;
          }
          if (func2(data1) < 1) {
            const err5 = { instancePath: instancePath + "/previousResultId", schemaPath: "#/allOf/0/then/properties/previousResultId/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
            if (vErrors === null) {
              vErrors = [err5];
            } else {
              vErrors.push(err5);
            }
            errors++;
          }
        } else {
          const err6 = { instancePath: instancePath + "/previousResultId", schemaPath: "#/allOf/0/then/properties/previousResultId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
          if (vErrors === null) {
            vErrors = [err6];
          } else {
            vErrors.push(err6);
          }
          errors++;
        }
      }
    }
    var _valid0 = _errs4 === errors;
    valid1 = _valid0;
  }
  if (!valid1) {
    const err7 = { instancePath, schemaPath: "#/allOf/0/if", keyword: "if", params: { failingKeyword: "then" }, message: 'must match "then" schema' };
    if (vErrors === null) {
      vErrors = [err7];
    } else {
      vErrors.push(err7);
    }
    errors++;
  }
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.title === void 0) {
      const err8 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "title" }, message: "must have required property 'title'" };
      if (vErrors === null) {
        vErrors = [err8];
      } else {
        vErrors.push(err8);
      }
      errors++;
    }
    if (data.prompt === void 0) {
      const err9 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "prompt" }, message: "must have required property 'prompt'" };
      if (vErrors === null) {
        vErrors = [err9];
      } else {
        vErrors.push(err9);
      }
      errors++;
    }
    if (data.documents === void 0) {
      const err10 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "documents" }, message: "must have required property 'documents'" };
      if (vErrors === null) {
        vErrors = [err10];
      } else {
        vErrors.push(err10);
      }
      errors++;
    }
    if (data.refinement === void 0) {
      const err11 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "refinement" }, message: "must have required property 'refinement'" };
      if (vErrors === null) {
        vErrors = [err11];
      } else {
        vErrors.push(err11);
      }
      errors++;
    }
    if (data.previousResultId === void 0) {
      const err12 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "previousResultId" }, message: "must have required property 'previousResultId'" };
      if (vErrors === null) {
        vErrors = [err12];
      } else {
        vErrors.push(err12);
      }
      errors++;
    }
    if (data.idempotencyKey === void 0) {
      const err13 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "idempotencyKey" }, message: "must have required property 'idempotencyKey'" };
      if (vErrors === null) {
        vErrors = [err13];
      } else {
        vErrors.push(err13);
      }
      errors++;
    }
    if (data.consentToModel === void 0) {
      const err14 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "consentToModel" }, message: "must have required property 'consentToModel'" };
      if (vErrors === null) {
        vErrors = [err14];
      } else {
        vErrors.push(err14);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!(key0 === "title" || key0 === "prompt" || key0 === "documents" || key0 === "refinement" || key0 === "previousResultId" || key0 === "idempotencyKey" || key0 === "consentToModel" || key0 === "designChange")) {
        const err15 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err15];
        } else {
          vErrors.push(err15);
        }
        errors++;
      }
    }
    if (data.title !== void 0) {
      let data2 = data.title;
      if (typeof data2 === "string") {
        if (func2(data2) > 160) {
          const err16 = { instancePath: instancePath + "/title", schemaPath: "#/properties/title/maxLength", keyword: "maxLength", params: { limit: 160 }, message: "must NOT have more than 160 characters" };
          if (vErrors === null) {
            vErrors = [err16];
          } else {
            vErrors.push(err16);
          }
          errors++;
        }
      } else {
        const err17 = { instancePath: instancePath + "/title", schemaPath: "#/properties/title/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err17];
        } else {
          vErrors.push(err17);
        }
        errors++;
      }
    }
    if (data.prompt !== void 0) {
      let data3 = data.prompt;
      if (typeof data3 === "string") {
        if (func2(data3) > 12e3) {
          const err18 = { instancePath: instancePath + "/prompt", schemaPath: "#/properties/prompt/maxLength", keyword: "maxLength", params: { limit: 12e3 }, message: "must NOT have more than 12000 characters" };
          if (vErrors === null) {
            vErrors = [err18];
          } else {
            vErrors.push(err18);
          }
          errors++;
        }
        if (func2(data3) < 10) {
          const err19 = { instancePath: instancePath + "/prompt", schemaPath: "#/properties/prompt/minLength", keyword: "minLength", params: { limit: 10 }, message: "must NOT have fewer than 10 characters" };
          if (vErrors === null) {
            vErrors = [err19];
          } else {
            vErrors.push(err19);
          }
          errors++;
        }
      } else {
        const err20 = { instancePath: instancePath + "/prompt", schemaPath: "#/properties/prompt/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err20];
        } else {
          vErrors.push(err20);
        }
        errors++;
      }
    }
    if (data.documents !== void 0) {
      let data4 = data.documents;
      if (Array.isArray(data4)) {
        if (data4.length > 5) {
          const err21 = { instancePath: instancePath + "/documents", schemaPath: "#/properties/documents/maxItems", keyword: "maxItems", params: { limit: 5 }, message: "must NOT have more than 5 items" };
          if (vErrors === null) {
            vErrors = [err21];
          } else {
            vErrors.push(err21);
          }
          errors++;
        }
        const len0 = data4.length;
        for (let i0 = 0; i0 < len0; i0++) {
          let data5 = data4[i0];
          if (data5 && typeof data5 == "object" && !Array.isArray(data5)) {
            if (data5.id === void 0) {
              const err22 = { instancePath: instancePath + "/documents/" + i0, schemaPath: "#/definitions/SourceDocument/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
              if (vErrors === null) {
                vErrors = [err22];
              } else {
                vErrors.push(err22);
              }
              errors++;
            }
            if (data5.name === void 0) {
              const err23 = { instancePath: instancePath + "/documents/" + i0, schemaPath: "#/definitions/SourceDocument/required", keyword: "required", params: { missingProperty: "name" }, message: "must have required property 'name'" };
              if (vErrors === null) {
                vErrors = [err23];
              } else {
                vErrors.push(err23);
              }
              errors++;
            }
            if (data5.text === void 0) {
              const err24 = { instancePath: instancePath + "/documents/" + i0, schemaPath: "#/definitions/SourceDocument/required", keyword: "required", params: { missingProperty: "text" }, message: "must have required property 'text'" };
              if (vErrors === null) {
                vErrors = [err24];
              } else {
                vErrors.push(err24);
              }
              errors++;
            }
            for (const key1 in data5) {
              if (!(key1 === "id" || key1 === "name" || key1 === "text")) {
                const err25 = { instancePath: instancePath + "/documents/" + i0, schemaPath: "#/definitions/SourceDocument/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key1 }, message: "must NOT have additional properties" };
                if (vErrors === null) {
                  vErrors = [err25];
                } else {
                  vErrors.push(err25);
                }
                errors++;
              }
            }
            if (data5.id !== void 0) {
              let data6 = data5.id;
              if (typeof data6 === "string") {
                if (func2(data6) > 128) {
                  const err26 = { instancePath: instancePath + "/documents/" + i0 + "/id", schemaPath: "#/definitions/SourceDocument/properties/id/maxLength", keyword: "maxLength", params: { limit: 128 }, message: "must NOT have more than 128 characters" };
                  if (vErrors === null) {
                    vErrors = [err26];
                  } else {
                    vErrors.push(err26);
                  }
                  errors++;
                }
                if (func2(data6) < 1) {
                  const err27 = { instancePath: instancePath + "/documents/" + i0 + "/id", schemaPath: "#/definitions/SourceDocument/properties/id/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                  if (vErrors === null) {
                    vErrors = [err27];
                  } else {
                    vErrors.push(err27);
                  }
                  errors++;
                }
              } else {
                const err28 = { instancePath: instancePath + "/documents/" + i0 + "/id", schemaPath: "#/definitions/SourceDocument/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err28];
                } else {
                  vErrors.push(err28);
                }
                errors++;
              }
            }
            if (data5.name !== void 0) {
              let data7 = data5.name;
              if (typeof data7 === "string") {
                if (func2(data7) > 255) {
                  const err29 = { instancePath: instancePath + "/documents/" + i0 + "/name", schemaPath: "#/definitions/SourceDocument/properties/name/maxLength", keyword: "maxLength", params: { limit: 255 }, message: "must NOT have more than 255 characters" };
                  if (vErrors === null) {
                    vErrors = [err29];
                  } else {
                    vErrors.push(err29);
                  }
                  errors++;
                }
                if (func2(data7) < 1) {
                  const err30 = { instancePath: instancePath + "/documents/" + i0 + "/name", schemaPath: "#/definitions/SourceDocument/properties/name/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                  if (vErrors === null) {
                    vErrors = [err30];
                  } else {
                    vErrors.push(err30);
                  }
                  errors++;
                }
              } else {
                const err31 = { instancePath: instancePath + "/documents/" + i0 + "/name", schemaPath: "#/definitions/SourceDocument/properties/name/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err31];
                } else {
                  vErrors.push(err31);
                }
                errors++;
              }
            }
            if (data5.text !== void 0) {
              let data8 = data5.text;
              if (typeof data8 === "string") {
                if (func2(data8) > 15e4) {
                  const err32 = { instancePath: instancePath + "/documents/" + i0 + "/text", schemaPath: "#/definitions/SourceDocument/properties/text/maxLength", keyword: "maxLength", params: { limit: 15e4 }, message: "must NOT have more than 150000 characters" };
                  if (vErrors === null) {
                    vErrors = [err32];
                  } else {
                    vErrors.push(err32);
                  }
                  errors++;
                }
                if (func2(data8) < 1) {
                  const err33 = { instancePath: instancePath + "/documents/" + i0 + "/text", schemaPath: "#/definitions/SourceDocument/properties/text/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
                  if (vErrors === null) {
                    vErrors = [err33];
                  } else {
                    vErrors.push(err33);
                  }
                  errors++;
                }
              } else {
                const err34 = { instancePath: instancePath + "/documents/" + i0 + "/text", schemaPath: "#/definitions/SourceDocument/properties/text/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err34];
                } else {
                  vErrors.push(err34);
                }
                errors++;
              }
            }
          } else {
            const err35 = { instancePath: instancePath + "/documents/" + i0, schemaPath: "#/definitions/SourceDocument/type", keyword: "type", params: { type: "object" }, message: "must be object" };
            if (vErrors === null) {
              vErrors = [err35];
            } else {
              vErrors.push(err35);
            }
            errors++;
          }
        }
      } else {
        const err36 = { instancePath: instancePath + "/documents", schemaPath: "#/properties/documents/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err36];
        } else {
          vErrors.push(err36);
        }
        errors++;
      }
    }
    if (data.refinement !== void 0) {
      let data9 = data.refinement;
      if (typeof data9 === "string") {
        if (func2(data9) > 4e3) {
          const err37 = { instancePath: instancePath + "/refinement", schemaPath: "#/properties/refinement/maxLength", keyword: "maxLength", params: { limit: 4e3 }, message: "must NOT have more than 4000 characters" };
          if (vErrors === null) {
            vErrors = [err37];
          } else {
            vErrors.push(err37);
          }
          errors++;
        }
      } else {
        const err38 = { instancePath: instancePath + "/refinement", schemaPath: "#/properties/refinement/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err38];
        } else {
          vErrors.push(err38);
        }
        errors++;
      }
    }
    if (data.previousResultId !== void 0) {
      let data10 = data.previousResultId;
      if (typeof data10 !== "string" && data10 !== null) {
        const err39 = { instancePath: instancePath + "/previousResultId", schemaPath: "#/properties/previousResultId/type", keyword: "type", params: { type: schema13.properties.previousResultId.type }, message: "must be string,null" };
        if (vErrors === null) {
          vErrors = [err39];
        } else {
          vErrors.push(err39);
        }
        errors++;
      }
      if (typeof data10 === "string") {
        if (func2(data10) > 80) {
          const err40 = { instancePath: instancePath + "/previousResultId", schemaPath: "#/properties/previousResultId/maxLength", keyword: "maxLength", params: { limit: 80 }, message: "must NOT have more than 80 characters" };
          if (vErrors === null) {
            vErrors = [err40];
          } else {
            vErrors.push(err40);
          }
          errors++;
        }
      }
    }
    if (data.idempotencyKey !== void 0) {
      let data11 = data.idempotencyKey;
      if (typeof data11 === "string") {
        if (func2(data11) > 128) {
          const err41 = { instancePath: instancePath + "/idempotencyKey", schemaPath: "#/properties/idempotencyKey/maxLength", keyword: "maxLength", params: { limit: 128 }, message: "must NOT have more than 128 characters" };
          if (vErrors === null) {
            vErrors = [err41];
          } else {
            vErrors.push(err41);
          }
          errors++;
        }
        if (func2(data11) < 8) {
          const err42 = { instancePath: instancePath + "/idempotencyKey", schemaPath: "#/properties/idempotencyKey/minLength", keyword: "minLength", params: { limit: 8 }, message: "must NOT have fewer than 8 characters" };
          if (vErrors === null) {
            vErrors = [err42];
          } else {
            vErrors.push(err42);
          }
          errors++;
        }
      } else {
        const err43 = { instancePath: instancePath + "/idempotencyKey", schemaPath: "#/properties/idempotencyKey/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err43];
        } else {
          vErrors.push(err43);
        }
        errors++;
      }
    }
    if (data.consentToModel !== void 0) {
      let data12 = data.consentToModel;
      if (typeof data12 !== "boolean") {
        const err44 = { instancePath: instancePath + "/consentToModel", schemaPath: "#/properties/consentToModel/type", keyword: "type", params: { type: "boolean" }, message: "must be boolean" };
        if (vErrors === null) {
          vErrors = [err44];
        } else {
          vErrors.push(err44);
        }
        errors++;
      }
      if (true !== data12) {
        const err45 = { instancePath: instancePath + "/consentToModel", schemaPath: "#/properties/consentToModel/const", keyword: "const", params: { allowedValue: true }, message: "must be equal to constant" };
        if (vErrors === null) {
          vErrors = [err45];
        } else {
          vErrors.push(err45);
        }
        errors++;
      }
    }
    if (data.designChange !== void 0) {
      if (!validate13(data.designChange, { instancePath: instancePath + "/designChange", parentData: data, parentDataProperty: "designChange", rootData })) {
        vErrors = vErrors === null ? validate13.errors : vErrors.concat(validate13.errors);
        errors = vErrors.length;
      }
    }
  } else {
    const err46 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err46];
    } else {
      vErrors.push(err46);
    }
    errors++;
  }
  validate55.errors = vErrors;
  return errors === 0;
}
function validate54(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  ;
  let vErrors = null;
  let errors = 0;
  if (!validate55(data, { instancePath, parentData, parentDataProperty, rootData })) {
    vErrors = vErrors === null ? validate55.errors : vErrors.concat(validate55.errors);
    errors = vErrors.length;
  }
  validate54.errors = vErrors;
  return errors === 0;
}
var requestBuildShape = validate58;
function validate58(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  ;
  let vErrors = null;
  let errors = 0;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.resultId === void 0) {
      const err0 = { instancePath, schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/required", keyword: "required", params: { missingProperty: "resultId" }, message: "must have required property 'resultId'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.optionId === void 0) {
      const err1 = { instancePath, schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/required", keyword: "required", params: { missingProperty: "optionId" }, message: "must have required property 'optionId'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    if (data.confirmGeneration === void 0) {
      const err2 = { instancePath, schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/required", keyword: "required", params: { missingProperty: "confirmGeneration" }, message: "must have required property 'confirmGeneration'" };
      if (vErrors === null) {
        vErrors = [err2];
      } else {
        vErrors.push(err2);
      }
      errors++;
    }
    if (data.idempotencyKey === void 0) {
      const err3 = { instancePath, schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/required", keyword: "required", params: { missingProperty: "idempotencyKey" }, message: "must have required property 'idempotencyKey'" };
      if (vErrors === null) {
        vErrors = [err3];
      } else {
        vErrors.push(err3);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!(key0 === "resultId" || key0 === "optionId" || key0 === "confirmGeneration" || key0 === "idempotencyKey")) {
        const err4 = { instancePath, schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err4];
        } else {
          vErrors.push(err4);
        }
        errors++;
      }
    }
    if (data.resultId !== void 0) {
      let data0 = data.resultId;
      if (typeof data0 === "string") {
        if (func2(data0) > 80) {
          const err5 = { instancePath: instancePath + "/resultId", schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/properties/resultId/maxLength", keyword: "maxLength", params: { limit: 80 }, message: "must NOT have more than 80 characters" };
          if (vErrors === null) {
            vErrors = [err5];
          } else {
            vErrors.push(err5);
          }
          errors++;
        }
        if (func2(data0) < 1) {
          const err6 = { instancePath: instancePath + "/resultId", schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/properties/resultId/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
          if (vErrors === null) {
            vErrors = [err6];
          } else {
            vErrors.push(err6);
          }
          errors++;
        }
      } else {
        const err7 = { instancePath: instancePath + "/resultId", schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/properties/resultId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err7];
        } else {
          vErrors.push(err7);
        }
        errors++;
      }
    }
    if (data.optionId !== void 0) {
      let data1 = data.optionId;
      if (typeof data1 === "string") {
        if (!pattern0.test(data1)) {
          const err8 = { instancePath: instancePath + "/optionId", schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/properties/optionId/pattern", keyword: "pattern", params: { pattern: "^[a-z][a-z0-9-]{0,39}$" }, message: 'must match pattern "^[a-z][a-z0-9-]{0,39}$"' };
          if (vErrors === null) {
            vErrors = [err8];
          } else {
            vErrors.push(err8);
          }
          errors++;
        }
      } else {
        const err9 = { instancePath: instancePath + "/optionId", schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/properties/optionId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err9];
        } else {
          vErrors.push(err9);
        }
        errors++;
      }
    }
    if (data.confirmGeneration !== void 0) {
      let data2 = data.confirmGeneration;
      if (typeof data2 !== "boolean") {
        const err10 = { instancePath: instancePath + "/confirmGeneration", schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/properties/confirmGeneration/type", keyword: "type", params: { type: "boolean" }, message: "must be boolean" };
        if (vErrors === null) {
          vErrors = [err10];
        } else {
          vErrors.push(err10);
        }
        errors++;
      }
      if (true !== data2) {
        const err11 = { instancePath: instancePath + "/confirmGeneration", schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/properties/confirmGeneration/const", keyword: "const", params: { allowedValue: true }, message: "must be equal to constant" };
        if (vErrors === null) {
          vErrors = [err11];
        } else {
          vErrors.push(err11);
        }
        errors++;
      }
    }
    if (data.idempotencyKey !== void 0) {
      let data3 = data.idempotencyKey;
      if (typeof data3 === "string") {
        if (func2(data3) > 128) {
          const err12 = { instancePath: instancePath + "/idempotencyKey", schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/properties/idempotencyKey/maxLength", keyword: "maxLength", params: { limit: 128 }, message: "must NOT have more than 128 characters" };
          if (vErrors === null) {
            vErrors = [err12];
          } else {
            vErrors.push(err12);
          }
          errors++;
        }
        if (func2(data3) < 8) {
          const err13 = { instancePath: instancePath + "/idempotencyKey", schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/properties/idempotencyKey/minLength", keyword: "minLength", params: { limit: 8 }, message: "must NOT have fewer than 8 characters" };
          if (vErrors === null) {
            vErrors = [err13];
          } else {
            vErrors.push(err13);
          }
          errors++;
        }
      } else {
        const err14 = { instancePath: instancePath + "/idempotencyKey", schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/properties/idempotencyKey/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err14];
        } else {
          vErrors.push(err14);
        }
        errors++;
      }
    }
  } else {
    const err15 = { instancePath, schemaPath: "urn:intent-to-impact:studio:1.0.0#/definitions/BuildRequest/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err15];
    } else {
      vErrors.push(err15);
    }
    errors++;
  }
  validate58.errors = vErrors;
  return errors === 0;
}
var historyShape = validate59;
var schema37 = { "type": "object", "additionalProperties": false, "properties": { "scope": { "type": "string", "enum": ["session", "workspace"] }, "runs": { "type": "array", "maxItems": 64, "items": { "$ref": "#/definitions/RunSummary" } } }, "required": ["scope", "runs"] };
var schema38 = { "type": "object", "additionalProperties": false, "properties": { "jobId": { "type": "string" }, "title": { "type": "string" }, "status": { "$ref": "#/definitions/StudioJob/properties/status" }, "createdAt": { "type": "string" }, "updatedAt": { "type": "string" }, "documentCount": { "type": "integer", "minimum": 0 }, "resultId": { "type": ["string", "null"] }, "previousResultId": { "type": ["string", "null"] }, "compiledPackageCount": { "type": "integer", "minimum": 0 }, "error": { "$ref": "#/definitions/StudioJob/properties/error" } }, "required": ["jobId", "title", "status", "createdAt", "updatedAt", "documentCount", "resultId", "previousResultId", "compiledPackageCount", "error"] };
var schema39 = { "type": "string", "enum": ["queued", "running", "succeeded", "failed"] };
function validate33(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  const _errs0 = errors;
  let valid0 = false;
  const _errs1 = errors;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.code === void 0) {
      const err0 = { instancePath, schemaPath: "#/definitions/StudioError/required", keyword: "required", params: { missingProperty: "code" }, message: "must have required property 'code'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.message === void 0) {
      const err1 = { instancePath, schemaPath: "#/definitions/StudioError/required", keyword: "required", params: { missingProperty: "message" }, message: "must have required property 'message'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    if (data.retryable === void 0) {
      const err2 = { instancePath, schemaPath: "#/definitions/StudioError/required", keyword: "required", params: { missingProperty: "retryable" }, message: "must have required property 'retryable'" };
      if (vErrors === null) {
        vErrors = [err2];
      } else {
        vErrors.push(err2);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!(key0 === "code" || key0 === "message" || key0 === "retryable")) {
        const err3 = { instancePath, schemaPath: "#/definitions/StudioError/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err3];
        } else {
          vErrors.push(err3);
        }
        errors++;
      }
    }
    if (data.code !== void 0) {
      if (typeof data.code !== "string") {
        const err4 = { instancePath: instancePath + "/code", schemaPath: "#/definitions/StudioError/properties/code/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err4];
        } else {
          vErrors.push(err4);
        }
        errors++;
      }
    }
    if (data.message !== void 0) {
      if (typeof data.message !== "string") {
        const err5 = { instancePath: instancePath + "/message", schemaPath: "#/definitions/StudioError/properties/message/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err5];
        } else {
          vErrors.push(err5);
        }
        errors++;
      }
    }
    if (data.retryable !== void 0) {
      if (typeof data.retryable !== "boolean") {
        const err6 = { instancePath: instancePath + "/retryable", schemaPath: "#/definitions/StudioError/properties/retryable/type", keyword: "type", params: { type: "boolean" }, message: "must be boolean" };
        if (vErrors === null) {
          vErrors = [err6];
        } else {
          vErrors.push(err6);
        }
        errors++;
      }
    }
  } else {
    const err7 = { instancePath, schemaPath: "#/definitions/StudioError/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err7];
    } else {
      vErrors.push(err7);
    }
    errors++;
  }
  var _valid0 = _errs1 === errors;
  valid0 = valid0 || _valid0;
  if (!valid0) {
    const _errs11 = errors;
    if (data !== null) {
      const err8 = { instancePath, schemaPath: "#/anyOf/1/type", keyword: "type", params: { type: "null" }, message: "must be null" };
      if (vErrors === null) {
        vErrors = [err8];
      } else {
        vErrors.push(err8);
      }
      errors++;
    }
    var _valid0 = _errs11 === errors;
    valid0 = valid0 || _valid0;
  }
  if (!valid0) {
    const err9 = { instancePath, schemaPath: "#/anyOf", keyword: "anyOf", params: {}, message: "must match a schema in anyOf" };
    if (vErrors === null) {
      vErrors = [err9];
    } else {
      vErrors.push(err9);
    }
    errors++;
  } else {
    errors = _errs0;
    if (vErrors !== null) {
      if (_errs0) {
        vErrors.length = _errs0;
      } else {
        vErrors = null;
      }
    }
  }
  validate33.errors = vErrors;
  return errors === 0;
}
function validate32(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.jobId === void 0) {
      const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "jobId" }, message: "must have required property 'jobId'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.title === void 0) {
      const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "title" }, message: "must have required property 'title'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    if (data.status === void 0) {
      const err2 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "status" }, message: "must have required property 'status'" };
      if (vErrors === null) {
        vErrors = [err2];
      } else {
        vErrors.push(err2);
      }
      errors++;
    }
    if (data.createdAt === void 0) {
      const err3 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "createdAt" }, message: "must have required property 'createdAt'" };
      if (vErrors === null) {
        vErrors = [err3];
      } else {
        vErrors.push(err3);
      }
      errors++;
    }
    if (data.updatedAt === void 0) {
      const err4 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "updatedAt" }, message: "must have required property 'updatedAt'" };
      if (vErrors === null) {
        vErrors = [err4];
      } else {
        vErrors.push(err4);
      }
      errors++;
    }
    if (data.documentCount === void 0) {
      const err5 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "documentCount" }, message: "must have required property 'documentCount'" };
      if (vErrors === null) {
        vErrors = [err5];
      } else {
        vErrors.push(err5);
      }
      errors++;
    }
    if (data.resultId === void 0) {
      const err6 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "resultId" }, message: "must have required property 'resultId'" };
      if (vErrors === null) {
        vErrors = [err6];
      } else {
        vErrors.push(err6);
      }
      errors++;
    }
    if (data.previousResultId === void 0) {
      const err7 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "previousResultId" }, message: "must have required property 'previousResultId'" };
      if (vErrors === null) {
        vErrors = [err7];
      } else {
        vErrors.push(err7);
      }
      errors++;
    }
    if (data.compiledPackageCount === void 0) {
      const err8 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "compiledPackageCount" }, message: "must have required property 'compiledPackageCount'" };
      if (vErrors === null) {
        vErrors = [err8];
      } else {
        vErrors.push(err8);
      }
      errors++;
    }
    if (data.error === void 0) {
      const err9 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "error" }, message: "must have required property 'error'" };
      if (vErrors === null) {
        vErrors = [err9];
      } else {
        vErrors.push(err9);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!func24.call(schema38.properties, key0)) {
        const err10 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err10];
        } else {
          vErrors.push(err10);
        }
        errors++;
      }
    }
    if (data.jobId !== void 0) {
      if (typeof data.jobId !== "string") {
        const err11 = { instancePath: instancePath + "/jobId", schemaPath: "#/properties/jobId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err11];
        } else {
          vErrors.push(err11);
        }
        errors++;
      }
    }
    if (data.title !== void 0) {
      if (typeof data.title !== "string") {
        const err12 = { instancePath: instancePath + "/title", schemaPath: "#/properties/title/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err12];
        } else {
          vErrors.push(err12);
        }
        errors++;
      }
    }
    if (data.status !== void 0) {
      let data2 = data.status;
      if (typeof data2 !== "string") {
        const err13 = { instancePath: instancePath + "/status", schemaPath: "#/definitions/StudioJob/properties/status/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err13];
        } else {
          vErrors.push(err13);
        }
        errors++;
      }
      if (!(data2 === "queued" || data2 === "running" || data2 === "succeeded" || data2 === "failed")) {
        const err14 = { instancePath: instancePath + "/status", schemaPath: "#/definitions/StudioJob/properties/status/enum", keyword: "enum", params: { allowedValues: schema39.enum }, message: "must be equal to one of the allowed values" };
        if (vErrors === null) {
          vErrors = [err14];
        } else {
          vErrors.push(err14);
        }
        errors++;
      }
    }
    if (data.createdAt !== void 0) {
      if (typeof data.createdAt !== "string") {
        const err15 = { instancePath: instancePath + "/createdAt", schemaPath: "#/properties/createdAt/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err15];
        } else {
          vErrors.push(err15);
        }
        errors++;
      }
    }
    if (data.updatedAt !== void 0) {
      if (typeof data.updatedAt !== "string") {
        const err16 = { instancePath: instancePath + "/updatedAt", schemaPath: "#/properties/updatedAt/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err16];
        } else {
          vErrors.push(err16);
        }
        errors++;
      }
    }
    if (data.documentCount !== void 0) {
      let data5 = data.documentCount;
      if (!(typeof data5 == "number" && (!(data5 % 1) && !isNaN(data5)))) {
        const err17 = { instancePath: instancePath + "/documentCount", schemaPath: "#/properties/documentCount/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
        if (vErrors === null) {
          vErrors = [err17];
        } else {
          vErrors.push(err17);
        }
        errors++;
      }
      if (typeof data5 == "number") {
        if (data5 < 0 || isNaN(data5)) {
          const err18 = { instancePath: instancePath + "/documentCount", schemaPath: "#/properties/documentCount/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
          if (vErrors === null) {
            vErrors = [err18];
          } else {
            vErrors.push(err18);
          }
          errors++;
        }
      }
    }
    if (data.resultId !== void 0) {
      let data6 = data.resultId;
      if (typeof data6 !== "string" && data6 !== null) {
        const err19 = { instancePath: instancePath + "/resultId", schemaPath: "#/properties/resultId/type", keyword: "type", params: { type: schema38.properties.resultId.type }, message: "must be string,null" };
        if (vErrors === null) {
          vErrors = [err19];
        } else {
          vErrors.push(err19);
        }
        errors++;
      }
    }
    if (data.previousResultId !== void 0) {
      let data7 = data.previousResultId;
      if (typeof data7 !== "string" && data7 !== null) {
        const err20 = { instancePath: instancePath + "/previousResultId", schemaPath: "#/properties/previousResultId/type", keyword: "type", params: { type: schema38.properties.previousResultId.type }, message: "must be string,null" };
        if (vErrors === null) {
          vErrors = [err20];
        } else {
          vErrors.push(err20);
        }
        errors++;
      }
    }
    if (data.compiledPackageCount !== void 0) {
      let data8 = data.compiledPackageCount;
      if (!(typeof data8 == "number" && (!(data8 % 1) && !isNaN(data8)))) {
        const err21 = { instancePath: instancePath + "/compiledPackageCount", schemaPath: "#/properties/compiledPackageCount/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
        if (vErrors === null) {
          vErrors = [err21];
        } else {
          vErrors.push(err21);
        }
        errors++;
      }
      if (typeof data8 == "number") {
        if (data8 < 0 || isNaN(data8)) {
          const err22 = { instancePath: instancePath + "/compiledPackageCount", schemaPath: "#/properties/compiledPackageCount/minimum", keyword: "minimum", params: { comparison: ">=", limit: 0 }, message: "must be >= 0" };
          if (vErrors === null) {
            vErrors = [err22];
          } else {
            vErrors.push(err22);
          }
          errors++;
        }
      }
    }
    if (data.error !== void 0) {
      if (!validate33(data.error, { instancePath: instancePath + "/error", parentData: data, parentDataProperty: "error", rootData })) {
        vErrors = vErrors === null ? validate33.errors : vErrors.concat(validate33.errors);
        errors = vErrors.length;
      }
    }
  } else {
    const err23 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err23];
    } else {
      vErrors.push(err23);
    }
    errors++;
  }
  validate32.errors = vErrors;
  return errors === 0;
}
function validate60(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.scope === void 0) {
      const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "scope" }, message: "must have required property 'scope'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.runs === void 0) {
      const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "runs" }, message: "must have required property 'runs'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!(key0 === "scope" || key0 === "runs")) {
        const err2 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err2];
        } else {
          vErrors.push(err2);
        }
        errors++;
      }
    }
    if (data.scope !== void 0) {
      let data0 = data.scope;
      if (typeof data0 !== "string") {
        const err3 = { instancePath: instancePath + "/scope", schemaPath: "#/properties/scope/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err3];
        } else {
          vErrors.push(err3);
        }
        errors++;
      }
      if (!(data0 === "session" || data0 === "workspace")) {
        const err4 = { instancePath: instancePath + "/scope", schemaPath: "#/properties/scope/enum", keyword: "enum", params: { allowedValues: schema37.properties.scope.enum }, message: "must be equal to one of the allowed values" };
        if (vErrors === null) {
          vErrors = [err4];
        } else {
          vErrors.push(err4);
        }
        errors++;
      }
    }
    if (data.runs !== void 0) {
      let data1 = data.runs;
      if (Array.isArray(data1)) {
        if (data1.length > 64) {
          const err5 = { instancePath: instancePath + "/runs", schemaPath: "#/properties/runs/maxItems", keyword: "maxItems", params: { limit: 64 }, message: "must NOT have more than 64 items" };
          if (vErrors === null) {
            vErrors = [err5];
          } else {
            vErrors.push(err5);
          }
          errors++;
        }
        const len0 = data1.length;
        for (let i0 = 0; i0 < len0; i0++) {
          if (!validate32(data1[i0], { instancePath: instancePath + "/runs/" + i0, parentData: data1, parentDataProperty: i0, rootData })) {
            vErrors = vErrors === null ? validate32.errors : vErrors.concat(validate32.errors);
            errors = vErrors.length;
          }
        }
      } else {
        const err6 = { instancePath: instancePath + "/runs", schemaPath: "#/properties/runs/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err6];
        } else {
          vErrors.push(err6);
        }
        errors++;
      }
    }
  } else {
    const err7 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err7];
    } else {
      vErrors.push(err7);
    }
    errors++;
  }
  validate60.errors = vErrors;
  return errors === 0;
}
function validate59(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  ;
  let vErrors = null;
  let errors = 0;
  if (!validate60(data, { instancePath, parentData, parentDataProperty, rootData })) {
    vErrors = vErrors === null ? validate60.errors : vErrors.concat(validate60.errors);
    errors = vErrors.length;
  }
  validate59.errors = vErrors;
  return errors === 0;
}
var savedRunShape = validate63;
var schema42 = { "type": "object", "additionalProperties": false, "properties": { "scope": { "type": "string", "enum": ["session", "workspace"] }, "summary": { "$ref": "#/definitions/RunSummary" }, "inputs": { "$ref": "#/definitions/SavedInputs" }, "job": { "$ref": "#/definitions/StudioJob" }, "builds": { "type": "array", "maxItems": 64, "items": { "$ref": "#/definitions/SavedBuild" } } }, "required": ["scope", "summary", "inputs", "job", "builds"] };
var schema49 = { "type": ["string", "null"], "maxLength": 80 };
function validate40(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  if (Array.isArray(data)) {
    if (data.length > 5) {
      const err0 = { instancePath, schemaPath: "#/maxItems", keyword: "maxItems", params: { limit: 5 }, message: "must NOT have more than 5 items" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    const len0 = data.length;
    for (let i0 = 0; i0 < len0; i0++) {
      let data0 = data[i0];
      if (data0 && typeof data0 == "object" && !Array.isArray(data0)) {
        if (data0.id === void 0) {
          const err1 = { instancePath: instancePath + "/" + i0, schemaPath: "#/definitions/SourceDocument/required", keyword: "required", params: { missingProperty: "id" }, message: "must have required property 'id'" };
          if (vErrors === null) {
            vErrors = [err1];
          } else {
            vErrors.push(err1);
          }
          errors++;
        }
        if (data0.name === void 0) {
          const err2 = { instancePath: instancePath + "/" + i0, schemaPath: "#/definitions/SourceDocument/required", keyword: "required", params: { missingProperty: "name" }, message: "must have required property 'name'" };
          if (vErrors === null) {
            vErrors = [err2];
          } else {
            vErrors.push(err2);
          }
          errors++;
        }
        if (data0.text === void 0) {
          const err3 = { instancePath: instancePath + "/" + i0, schemaPath: "#/definitions/SourceDocument/required", keyword: "required", params: { missingProperty: "text" }, message: "must have required property 'text'" };
          if (vErrors === null) {
            vErrors = [err3];
          } else {
            vErrors.push(err3);
          }
          errors++;
        }
        for (const key0 in data0) {
          if (!(key0 === "id" || key0 === "name" || key0 === "text")) {
            const err4 = { instancePath: instancePath + "/" + i0, schemaPath: "#/definitions/SourceDocument/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
            if (vErrors === null) {
              vErrors = [err4];
            } else {
              vErrors.push(err4);
            }
            errors++;
          }
        }
        if (data0.id !== void 0) {
          let data1 = data0.id;
          if (typeof data1 === "string") {
            if (func2(data1) > 128) {
              const err5 = { instancePath: instancePath + "/" + i0 + "/id", schemaPath: "#/definitions/SourceDocument/properties/id/maxLength", keyword: "maxLength", params: { limit: 128 }, message: "must NOT have more than 128 characters" };
              if (vErrors === null) {
                vErrors = [err5];
              } else {
                vErrors.push(err5);
              }
              errors++;
            }
            if (func2(data1) < 1) {
              const err6 = { instancePath: instancePath + "/" + i0 + "/id", schemaPath: "#/definitions/SourceDocument/properties/id/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
              if (vErrors === null) {
                vErrors = [err6];
              } else {
                vErrors.push(err6);
              }
              errors++;
            }
          } else {
            const err7 = { instancePath: instancePath + "/" + i0 + "/id", schemaPath: "#/definitions/SourceDocument/properties/id/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err7];
            } else {
              vErrors.push(err7);
            }
            errors++;
          }
        }
        if (data0.name !== void 0) {
          let data2 = data0.name;
          if (typeof data2 === "string") {
            if (func2(data2) > 255) {
              const err8 = { instancePath: instancePath + "/" + i0 + "/name", schemaPath: "#/definitions/SourceDocument/properties/name/maxLength", keyword: "maxLength", params: { limit: 255 }, message: "must NOT have more than 255 characters" };
              if (vErrors === null) {
                vErrors = [err8];
              } else {
                vErrors.push(err8);
              }
              errors++;
            }
            if (func2(data2) < 1) {
              const err9 = { instancePath: instancePath + "/" + i0 + "/name", schemaPath: "#/definitions/SourceDocument/properties/name/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
              if (vErrors === null) {
                vErrors = [err9];
              } else {
                vErrors.push(err9);
              }
              errors++;
            }
          } else {
            const err10 = { instancePath: instancePath + "/" + i0 + "/name", schemaPath: "#/definitions/SourceDocument/properties/name/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err10];
            } else {
              vErrors.push(err10);
            }
            errors++;
          }
        }
        if (data0.text !== void 0) {
          let data3 = data0.text;
          if (typeof data3 === "string") {
            if (func2(data3) > 15e4) {
              const err11 = { instancePath: instancePath + "/" + i0 + "/text", schemaPath: "#/definitions/SourceDocument/properties/text/maxLength", keyword: "maxLength", params: { limit: 15e4 }, message: "must NOT have more than 150000 characters" };
              if (vErrors === null) {
                vErrors = [err11];
              } else {
                vErrors.push(err11);
              }
              errors++;
            }
            if (func2(data3) < 1) {
              const err12 = { instancePath: instancePath + "/" + i0 + "/text", schemaPath: "#/definitions/SourceDocument/properties/text/minLength", keyword: "minLength", params: { limit: 1 }, message: "must NOT have fewer than 1 characters" };
              if (vErrors === null) {
                vErrors = [err12];
              } else {
                vErrors.push(err12);
              }
              errors++;
            }
          } else {
            const err13 = { instancePath: instancePath + "/" + i0 + "/text", schemaPath: "#/definitions/SourceDocument/properties/text/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err13];
            } else {
              vErrors.push(err13);
            }
            errors++;
          }
        }
      } else {
        const err14 = { instancePath: instancePath + "/" + i0, schemaPath: "#/definitions/SourceDocument/type", keyword: "type", params: { type: "object" }, message: "must be object" };
        if (vErrors === null) {
          vErrors = [err14];
        } else {
          vErrors.push(err14);
        }
        errors++;
      }
    }
  } else {
    const err15 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "array" }, message: "must be array" };
    if (vErrors === null) {
      vErrors = [err15];
    } else {
      vErrors.push(err15);
    }
    errors++;
  }
  validate40.errors = vErrors;
  return errors === 0;
}
function validate39(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.title === void 0) {
      const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "title" }, message: "must have required property 'title'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.prompt === void 0) {
      const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "prompt" }, message: "must have required property 'prompt'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    if (data.documents === void 0) {
      const err2 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "documents" }, message: "must have required property 'documents'" };
      if (vErrors === null) {
        vErrors = [err2];
      } else {
        vErrors.push(err2);
      }
      errors++;
    }
    if (data.refinement === void 0) {
      const err3 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "refinement" }, message: "must have required property 'refinement'" };
      if (vErrors === null) {
        vErrors = [err3];
      } else {
        vErrors.push(err3);
      }
      errors++;
    }
    if (data.previousResultId === void 0) {
      const err4 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "previousResultId" }, message: "must have required property 'previousResultId'" };
      if (vErrors === null) {
        vErrors = [err4];
      } else {
        vErrors.push(err4);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!(key0 === "title" || key0 === "prompt" || key0 === "documents" || key0 === "refinement" || key0 === "previousResultId")) {
        const err5 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err5];
        } else {
          vErrors.push(err5);
        }
        errors++;
      }
    }
    if (data.title !== void 0) {
      let data0 = data.title;
      if (typeof data0 === "string") {
        if (func2(data0) > 160) {
          const err6 = { instancePath: instancePath + "/title", schemaPath: "#/definitions/AnalysisRequest/properties/title/maxLength", keyword: "maxLength", params: { limit: 160 }, message: "must NOT have more than 160 characters" };
          if (vErrors === null) {
            vErrors = [err6];
          } else {
            vErrors.push(err6);
          }
          errors++;
        }
      } else {
        const err7 = { instancePath: instancePath + "/title", schemaPath: "#/definitions/AnalysisRequest/properties/title/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err7];
        } else {
          vErrors.push(err7);
        }
        errors++;
      }
    }
    if (data.prompt !== void 0) {
      let data1 = data.prompt;
      if (typeof data1 === "string") {
        if (func2(data1) > 12e3) {
          const err8 = { instancePath: instancePath + "/prompt", schemaPath: "#/definitions/AnalysisRequest/properties/prompt/maxLength", keyword: "maxLength", params: { limit: 12e3 }, message: "must NOT have more than 12000 characters" };
          if (vErrors === null) {
            vErrors = [err8];
          } else {
            vErrors.push(err8);
          }
          errors++;
        }
        if (func2(data1) < 10) {
          const err9 = { instancePath: instancePath + "/prompt", schemaPath: "#/definitions/AnalysisRequest/properties/prompt/minLength", keyword: "minLength", params: { limit: 10 }, message: "must NOT have fewer than 10 characters" };
          if (vErrors === null) {
            vErrors = [err9];
          } else {
            vErrors.push(err9);
          }
          errors++;
        }
      } else {
        const err10 = { instancePath: instancePath + "/prompt", schemaPath: "#/definitions/AnalysisRequest/properties/prompt/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err10];
        } else {
          vErrors.push(err10);
        }
        errors++;
      }
    }
    if (data.documents !== void 0) {
      if (!validate40(data.documents, { instancePath: instancePath + "/documents", parentData: data, parentDataProperty: "documents", rootData })) {
        vErrors = vErrors === null ? validate40.errors : vErrors.concat(validate40.errors);
        errors = vErrors.length;
      }
    }
    if (data.refinement !== void 0) {
      let data3 = data.refinement;
      if (typeof data3 === "string") {
        if (func2(data3) > 4e3) {
          const err11 = { instancePath: instancePath + "/refinement", schemaPath: "#/definitions/AnalysisRequest/properties/refinement/maxLength", keyword: "maxLength", params: { limit: 4e3 }, message: "must NOT have more than 4000 characters" };
          if (vErrors === null) {
            vErrors = [err11];
          } else {
            vErrors.push(err11);
          }
          errors++;
        }
      } else {
        const err12 = { instancePath: instancePath + "/refinement", schemaPath: "#/definitions/AnalysisRequest/properties/refinement/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err12];
        } else {
          vErrors.push(err12);
        }
        errors++;
      }
    }
    if (data.previousResultId !== void 0) {
      let data4 = data.previousResultId;
      if (typeof data4 !== "string" && data4 !== null) {
        const err13 = { instancePath: instancePath + "/previousResultId", schemaPath: "#/definitions/AnalysisRequest/properties/previousResultId/type", keyword: "type", params: { type: schema49.type }, message: "must be string,null" };
        if (vErrors === null) {
          vErrors = [err13];
        } else {
          vErrors.push(err13);
        }
        errors++;
      }
      if (typeof data4 === "string") {
        if (func2(data4) > 80) {
          const err14 = { instancePath: instancePath + "/previousResultId", schemaPath: "#/definitions/AnalysisRequest/properties/previousResultId/maxLength", keyword: "maxLength", params: { limit: 80 }, message: "must NOT have more than 80 characters" };
          if (vErrors === null) {
            vErrors = [err14];
          } else {
            vErrors.push(err14);
          }
          errors++;
        }
      }
    }
  } else {
    const err15 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err15];
    } else {
      vErrors.push(err15);
    }
    errors++;
  }
  validate39.errors = vErrors;
  return errors === 0;
}
function validate22(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.jobId === void 0) {
      const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "jobId" }, message: "must have required property 'jobId'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.status === void 0) {
      const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "status" }, message: "must have required property 'status'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    if (data.events === void 0) {
      const err2 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "events" }, message: "must have required property 'events'" };
      if (vErrors === null) {
        vErrors = [err2];
      } else {
        vErrors.push(err2);
      }
      errors++;
    }
    if (data.result === void 0) {
      const err3 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "result" }, message: "must have required property 'result'" };
      if (vErrors === null) {
        vErrors = [err3];
      } else {
        vErrors.push(err3);
      }
      errors++;
    }
    if (data.error === void 0) {
      const err4 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "error" }, message: "must have required property 'error'" };
      if (vErrors === null) {
        vErrors = [err4];
      } else {
        vErrors.push(err4);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!(key0 === "jobId" || key0 === "status" || key0 === "events" || key0 === "result" || key0 === "error" || key0 === "changeApproval")) {
        const err5 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err5];
        } else {
          vErrors.push(err5);
        }
        errors++;
      }
    }
    if (data.jobId !== void 0) {
      if (typeof data.jobId !== "string") {
        const err6 = { instancePath: instancePath + "/jobId", schemaPath: "#/properties/jobId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err6];
        } else {
          vErrors.push(err6);
        }
        errors++;
      }
    }
    if (data.status !== void 0) {
      let data1 = data.status;
      if (typeof data1 !== "string") {
        const err7 = { instancePath: instancePath + "/status", schemaPath: "#/properties/status/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err7];
        } else {
          vErrors.push(err7);
        }
        errors++;
      }
      if (!(data1 === "queued" || data1 === "running" || data1 === "succeeded" || data1 === "failed")) {
        const err8 = { instancePath: instancePath + "/status", schemaPath: "#/properties/status/enum", keyword: "enum", params: { allowedValues: schema25.properties.status.enum }, message: "must be equal to one of the allowed values" };
        if (vErrors === null) {
          vErrors = [err8];
        } else {
          vErrors.push(err8);
        }
        errors++;
      }
    }
    if (data.events !== void 0) {
      let data2 = data.events;
      if (Array.isArray(data2)) {
        const len0 = data2.length;
        for (let i0 = 0; i0 < len0; i0++) {
          let data3 = data2[i0];
          if (data3 && typeof data3 == "object" && !Array.isArray(data3)) {
            if (data3.sequence === void 0) {
              const err9 = { instancePath: instancePath + "/events/" + i0, schemaPath: "#/definitions/StudioEvent/required", keyword: "required", params: { missingProperty: "sequence" }, message: "must have required property 'sequence'" };
              if (vErrors === null) {
                vErrors = [err9];
              } else {
                vErrors.push(err9);
              }
              errors++;
            }
            if (data3.stage === void 0) {
              const err10 = { instancePath: instancePath + "/events/" + i0, schemaPath: "#/definitions/StudioEvent/required", keyword: "required", params: { missingProperty: "stage" }, message: "must have required property 'stage'" };
              if (vErrors === null) {
                vErrors = [err10];
              } else {
                vErrors.push(err10);
              }
              errors++;
            }
            if (data3.message === void 0) {
              const err11 = { instancePath: instancePath + "/events/" + i0, schemaPath: "#/definitions/StudioEvent/required", keyword: "required", params: { missingProperty: "message" }, message: "must have required property 'message'" };
              if (vErrors === null) {
                vErrors = [err11];
              } else {
                vErrors.push(err11);
              }
              errors++;
            }
            if (data3.at === void 0) {
              const err12 = { instancePath: instancePath + "/events/" + i0, schemaPath: "#/definitions/StudioEvent/required", keyword: "required", params: { missingProperty: "at" }, message: "must have required property 'at'" };
              if (vErrors === null) {
                vErrors = [err12];
              } else {
                vErrors.push(err12);
              }
              errors++;
            }
            for (const key1 in data3) {
              if (!(key1 === "sequence" || key1 === "stage" || key1 === "message" || key1 === "at")) {
                const err13 = { instancePath: instancePath + "/events/" + i0, schemaPath: "#/definitions/StudioEvent/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key1 }, message: "must NOT have additional properties" };
                if (vErrors === null) {
                  vErrors = [err13];
                } else {
                  vErrors.push(err13);
                }
                errors++;
              }
            }
            if (data3.sequence !== void 0) {
              let data4 = data3.sequence;
              if (!(typeof data4 == "number" && (!(data4 % 1) && !isNaN(data4)))) {
                const err14 = { instancePath: instancePath + "/events/" + i0 + "/sequence", schemaPath: "#/definitions/StudioEvent/properties/sequence/type", keyword: "type", params: { type: "integer" }, message: "must be integer" };
                if (vErrors === null) {
                  vErrors = [err14];
                } else {
                  vErrors.push(err14);
                }
                errors++;
              }
              if (typeof data4 == "number") {
                if (data4 < 1 || isNaN(data4)) {
                  const err15 = { instancePath: instancePath + "/events/" + i0 + "/sequence", schemaPath: "#/definitions/StudioEvent/properties/sequence/minimum", keyword: "minimum", params: { comparison: ">=", limit: 1 }, message: "must be >= 1" };
                  if (vErrors === null) {
                    vErrors = [err15];
                  } else {
                    vErrors.push(err15);
                  }
                  errors++;
                }
              }
            }
            if (data3.stage !== void 0) {
              let data5 = data3.stage;
              if (typeof data5 !== "string") {
                const err16 = { instancePath: instancePath + "/events/" + i0 + "/stage", schemaPath: "#/definitions/StudioEvent/properties/stage/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err16];
                } else {
                  vErrors.push(err16);
                }
                errors++;
              }
              if (!(data5 === "intake" || data5 === "synthesis" || data5 === "assurance" || data5 === "complete" || data5 === "error")) {
                const err17 = { instancePath: instancePath + "/events/" + i0 + "/stage", schemaPath: "#/definitions/StudioEvent/properties/stage/enum", keyword: "enum", params: { allowedValues: schema26.properties.stage.enum }, message: "must be equal to one of the allowed values" };
                if (vErrors === null) {
                  vErrors = [err17];
                } else {
                  vErrors.push(err17);
                }
                errors++;
              }
            }
            if (data3.message !== void 0) {
              if (typeof data3.message !== "string") {
                const err18 = { instancePath: instancePath + "/events/" + i0 + "/message", schemaPath: "#/definitions/StudioEvent/properties/message/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err18];
                } else {
                  vErrors.push(err18);
                }
                errors++;
              }
            }
            if (data3.at !== void 0) {
              if (typeof data3.at !== "string") {
                const err19 = { instancePath: instancePath + "/events/" + i0 + "/at", schemaPath: "#/definitions/StudioEvent/properties/at/type", keyword: "type", params: { type: "string" }, message: "must be string" };
                if (vErrors === null) {
                  vErrors = [err19];
                } else {
                  vErrors.push(err19);
                }
                errors++;
              }
            }
          } else {
            const err20 = { instancePath: instancePath + "/events/" + i0, schemaPath: "#/definitions/StudioEvent/type", keyword: "type", params: { type: "object" }, message: "must be object" };
            if (vErrors === null) {
              vErrors = [err20];
            } else {
              vErrors.push(err20);
            }
            errors++;
          }
        }
      } else {
        const err21 = { instancePath: instancePath + "/events", schemaPath: "#/properties/events/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err21];
        } else {
          vErrors.push(err21);
        }
        errors++;
      }
    }
    if (data.result !== void 0) {
      let data8 = data.result;
      const _errs21 = errors;
      let valid5 = false;
      const _errs22 = errors;
      if (!validate23(data8, { instancePath: instancePath + "/result", parentData: data, parentDataProperty: "result", rootData })) {
        vErrors = vErrors === null ? validate23.errors : vErrors.concat(validate23.errors);
        errors = vErrors.length;
      }
      var _valid0 = _errs22 === errors;
      valid5 = valid5 || _valid0;
      if (!valid5) {
        const _errs23 = errors;
        if (data8 !== null) {
          const err22 = { instancePath: instancePath + "/result", schemaPath: "#/properties/result/anyOf/1/type", keyword: "type", params: { type: "null" }, message: "must be null" };
          if (vErrors === null) {
            vErrors = [err22];
          } else {
            vErrors.push(err22);
          }
          errors++;
        }
        var _valid0 = _errs23 === errors;
        valid5 = valid5 || _valid0;
      }
      if (!valid5) {
        const err23 = { instancePath: instancePath + "/result", schemaPath: "#/properties/result/anyOf", keyword: "anyOf", params: {}, message: "must match a schema in anyOf" };
        if (vErrors === null) {
          vErrors = [err23];
        } else {
          vErrors.push(err23);
        }
        errors++;
      } else {
        errors = _errs21;
        if (vErrors !== null) {
          if (_errs21) {
            vErrors.length = _errs21;
          } else {
            vErrors = null;
          }
        }
      }
    }
    if (data.error !== void 0) {
      let data9 = data.error;
      const _errs26 = errors;
      let valid6 = false;
      const _errs27 = errors;
      if (data9 && typeof data9 == "object" && !Array.isArray(data9)) {
        if (data9.code === void 0) {
          const err24 = { instancePath: instancePath + "/error", schemaPath: "#/definitions/StudioError/required", keyword: "required", params: { missingProperty: "code" }, message: "must have required property 'code'" };
          if (vErrors === null) {
            vErrors = [err24];
          } else {
            vErrors.push(err24);
          }
          errors++;
        }
        if (data9.message === void 0) {
          const err25 = { instancePath: instancePath + "/error", schemaPath: "#/definitions/StudioError/required", keyword: "required", params: { missingProperty: "message" }, message: "must have required property 'message'" };
          if (vErrors === null) {
            vErrors = [err25];
          } else {
            vErrors.push(err25);
          }
          errors++;
        }
        if (data9.retryable === void 0) {
          const err26 = { instancePath: instancePath + "/error", schemaPath: "#/definitions/StudioError/required", keyword: "required", params: { missingProperty: "retryable" }, message: "must have required property 'retryable'" };
          if (vErrors === null) {
            vErrors = [err26];
          } else {
            vErrors.push(err26);
          }
          errors++;
        }
        for (const key2 in data9) {
          if (!(key2 === "code" || key2 === "message" || key2 === "retryable")) {
            const err27 = { instancePath: instancePath + "/error", schemaPath: "#/definitions/StudioError/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key2 }, message: "must NOT have additional properties" };
            if (vErrors === null) {
              vErrors = [err27];
            } else {
              vErrors.push(err27);
            }
            errors++;
          }
        }
        if (data9.code !== void 0) {
          if (typeof data9.code !== "string") {
            const err28 = { instancePath: instancePath + "/error/code", schemaPath: "#/definitions/StudioError/properties/code/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err28];
            } else {
              vErrors.push(err28);
            }
            errors++;
          }
        }
        if (data9.message !== void 0) {
          if (typeof data9.message !== "string") {
            const err29 = { instancePath: instancePath + "/error/message", schemaPath: "#/definitions/StudioError/properties/message/type", keyword: "type", params: { type: "string" }, message: "must be string" };
            if (vErrors === null) {
              vErrors = [err29];
            } else {
              vErrors.push(err29);
            }
            errors++;
          }
        }
        if (data9.retryable !== void 0) {
          if (typeof data9.retryable !== "boolean") {
            const err30 = { instancePath: instancePath + "/error/retryable", schemaPath: "#/definitions/StudioError/properties/retryable/type", keyword: "type", params: { type: "boolean" }, message: "must be boolean" };
            if (vErrors === null) {
              vErrors = [err30];
            } else {
              vErrors.push(err30);
            }
            errors++;
          }
        }
      } else {
        const err31 = { instancePath: instancePath + "/error", schemaPath: "#/definitions/StudioError/type", keyword: "type", params: { type: "object" }, message: "must be object" };
        if (vErrors === null) {
          vErrors = [err31];
        } else {
          vErrors.push(err31);
        }
        errors++;
      }
      var _valid1 = _errs27 === errors;
      valid6 = valid6 || _valid1;
      if (!valid6) {
        const _errs37 = errors;
        if (data9 !== null) {
          const err32 = { instancePath: instancePath + "/error", schemaPath: "#/properties/error/anyOf/1/type", keyword: "type", params: { type: "null" }, message: "must be null" };
          if (vErrors === null) {
            vErrors = [err32];
          } else {
            vErrors.push(err32);
          }
          errors++;
        }
        var _valid1 = _errs37 === errors;
        valid6 = valid6 || _valid1;
      }
      if (!valid6) {
        const err33 = { instancePath: instancePath + "/error", schemaPath: "#/properties/error/anyOf", keyword: "anyOf", params: {}, message: "must match a schema in anyOf" };
        if (vErrors === null) {
          vErrors = [err33];
        } else {
          vErrors.push(err33);
        }
        errors++;
      } else {
        errors = _errs26;
        if (vErrors !== null) {
          if (_errs26) {
            vErrors.length = _errs26;
          } else {
            vErrors = null;
          }
        }
      }
    }
    if (data.changeApproval !== void 0) {
      if (!validate26(data.changeApproval, { instancePath: instancePath + "/changeApproval", parentData: data, parentDataProperty: "changeApproval", rootData })) {
        vErrors = vErrors === null ? validate26.errors : vErrors.concat(validate26.errors);
        errors = vErrors.length;
      }
    }
  } else {
    const err34 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err34];
    } else {
      vErrors.push(err34);
    }
    errors++;
  }
  validate22.errors = vErrors;
  return errors === 0;
}
var schema50 = { "type": "object", "additionalProperties": false, "properties": { "buildId": { "type": "string" }, "resultId": { "type": "string" }, "optionId": { "type": "string" }, "status": { "$ref": "#/definitions/BuildResult/properties/status" }, "compilerVersion": { "type": ["string", "null"] }, "exitCode": { "type": ["integer", "null"] } }, "required": ["buildId", "resultId", "optionId", "status", "compilerVersion", "exitCode"] };
var schema51 = { "type": "string", "enum": ["compiled", "failed", "blocked"] };
function validate44(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.buildId === void 0) {
      const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "buildId" }, message: "must have required property 'buildId'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.resultId === void 0) {
      const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "resultId" }, message: "must have required property 'resultId'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    if (data.optionId === void 0) {
      const err2 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "optionId" }, message: "must have required property 'optionId'" };
      if (vErrors === null) {
        vErrors = [err2];
      } else {
        vErrors.push(err2);
      }
      errors++;
    }
    if (data.status === void 0) {
      const err3 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "status" }, message: "must have required property 'status'" };
      if (vErrors === null) {
        vErrors = [err3];
      } else {
        vErrors.push(err3);
      }
      errors++;
    }
    if (data.compilerVersion === void 0) {
      const err4 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "compilerVersion" }, message: "must have required property 'compilerVersion'" };
      if (vErrors === null) {
        vErrors = [err4];
      } else {
        vErrors.push(err4);
      }
      errors++;
    }
    if (data.exitCode === void 0) {
      const err5 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "exitCode" }, message: "must have required property 'exitCode'" };
      if (vErrors === null) {
        vErrors = [err5];
      } else {
        vErrors.push(err5);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!(key0 === "buildId" || key0 === "resultId" || key0 === "optionId" || key0 === "status" || key0 === "compilerVersion" || key0 === "exitCode")) {
        const err6 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err6];
        } else {
          vErrors.push(err6);
        }
        errors++;
      }
    }
    if (data.buildId !== void 0) {
      if (typeof data.buildId !== "string") {
        const err7 = { instancePath: instancePath + "/buildId", schemaPath: "#/properties/buildId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err7];
        } else {
          vErrors.push(err7);
        }
        errors++;
      }
    }
    if (data.resultId !== void 0) {
      if (typeof data.resultId !== "string") {
        const err8 = { instancePath: instancePath + "/resultId", schemaPath: "#/properties/resultId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err8];
        } else {
          vErrors.push(err8);
        }
        errors++;
      }
    }
    if (data.optionId !== void 0) {
      if (typeof data.optionId !== "string") {
        const err9 = { instancePath: instancePath + "/optionId", schemaPath: "#/properties/optionId/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err9];
        } else {
          vErrors.push(err9);
        }
        errors++;
      }
    }
    if (data.status !== void 0) {
      let data3 = data.status;
      if (typeof data3 !== "string") {
        const err10 = { instancePath: instancePath + "/status", schemaPath: "#/definitions/BuildResult/properties/status/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err10];
        } else {
          vErrors.push(err10);
        }
        errors++;
      }
      if (!(data3 === "compiled" || data3 === "failed" || data3 === "blocked")) {
        const err11 = { instancePath: instancePath + "/status", schemaPath: "#/definitions/BuildResult/properties/status/enum", keyword: "enum", params: { allowedValues: schema51.enum }, message: "must be equal to one of the allowed values" };
        if (vErrors === null) {
          vErrors = [err11];
        } else {
          vErrors.push(err11);
        }
        errors++;
      }
    }
    if (data.compilerVersion !== void 0) {
      let data4 = data.compilerVersion;
      if (typeof data4 !== "string" && data4 !== null) {
        const err12 = { instancePath: instancePath + "/compilerVersion", schemaPath: "#/properties/compilerVersion/type", keyword: "type", params: { type: schema50.properties.compilerVersion.type }, message: "must be string,null" };
        if (vErrors === null) {
          vErrors = [err12];
        } else {
          vErrors.push(err12);
        }
        errors++;
      }
    }
    if (data.exitCode !== void 0) {
      let data5 = data.exitCode;
      if (!(typeof data5 == "number" && (!(data5 % 1) && !isNaN(data5))) && data5 !== null) {
        const err13 = { instancePath: instancePath + "/exitCode", schemaPath: "#/properties/exitCode/type", keyword: "type", params: { type: schema50.properties.exitCode.type }, message: "must be integer,null" };
        if (vErrors === null) {
          vErrors = [err13];
        } else {
          vErrors.push(err13);
        }
        errors++;
      }
    }
  } else {
    const err14 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err14];
    } else {
      vErrors.push(err14);
    }
    errors++;
  }
  validate44.errors = vErrors;
  return errors === 0;
}
function validate64(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  let vErrors = null;
  let errors = 0;
  if (data && typeof data == "object" && !Array.isArray(data)) {
    if (data.scope === void 0) {
      const err0 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "scope" }, message: "must have required property 'scope'" };
      if (vErrors === null) {
        vErrors = [err0];
      } else {
        vErrors.push(err0);
      }
      errors++;
    }
    if (data.summary === void 0) {
      const err1 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "summary" }, message: "must have required property 'summary'" };
      if (vErrors === null) {
        vErrors = [err1];
      } else {
        vErrors.push(err1);
      }
      errors++;
    }
    if (data.inputs === void 0) {
      const err2 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "inputs" }, message: "must have required property 'inputs'" };
      if (vErrors === null) {
        vErrors = [err2];
      } else {
        vErrors.push(err2);
      }
      errors++;
    }
    if (data.job === void 0) {
      const err3 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "job" }, message: "must have required property 'job'" };
      if (vErrors === null) {
        vErrors = [err3];
      } else {
        vErrors.push(err3);
      }
      errors++;
    }
    if (data.builds === void 0) {
      const err4 = { instancePath, schemaPath: "#/required", keyword: "required", params: { missingProperty: "builds" }, message: "must have required property 'builds'" };
      if (vErrors === null) {
        vErrors = [err4];
      } else {
        vErrors.push(err4);
      }
      errors++;
    }
    for (const key0 in data) {
      if (!(key0 === "scope" || key0 === "summary" || key0 === "inputs" || key0 === "job" || key0 === "builds")) {
        const err5 = { instancePath, schemaPath: "#/additionalProperties", keyword: "additionalProperties", params: { additionalProperty: key0 }, message: "must NOT have additional properties" };
        if (vErrors === null) {
          vErrors = [err5];
        } else {
          vErrors.push(err5);
        }
        errors++;
      }
    }
    if (data.scope !== void 0) {
      let data0 = data.scope;
      if (typeof data0 !== "string") {
        const err6 = { instancePath: instancePath + "/scope", schemaPath: "#/properties/scope/type", keyword: "type", params: { type: "string" }, message: "must be string" };
        if (vErrors === null) {
          vErrors = [err6];
        } else {
          vErrors.push(err6);
        }
        errors++;
      }
      if (!(data0 === "session" || data0 === "workspace")) {
        const err7 = { instancePath: instancePath + "/scope", schemaPath: "#/properties/scope/enum", keyword: "enum", params: { allowedValues: schema42.properties.scope.enum }, message: "must be equal to one of the allowed values" };
        if (vErrors === null) {
          vErrors = [err7];
        } else {
          vErrors.push(err7);
        }
        errors++;
      }
    }
    if (data.summary !== void 0) {
      if (!validate32(data.summary, { instancePath: instancePath + "/summary", parentData: data, parentDataProperty: "summary", rootData })) {
        vErrors = vErrors === null ? validate32.errors : vErrors.concat(validate32.errors);
        errors = vErrors.length;
      }
    }
    if (data.inputs !== void 0) {
      if (!validate39(data.inputs, { instancePath: instancePath + "/inputs", parentData: data, parentDataProperty: "inputs", rootData })) {
        vErrors = vErrors === null ? validate39.errors : vErrors.concat(validate39.errors);
        errors = vErrors.length;
      }
    }
    if (data.job !== void 0) {
      if (!validate22(data.job, { instancePath: instancePath + "/job", parentData: data, parentDataProperty: "job", rootData })) {
        vErrors = vErrors === null ? validate22.errors : vErrors.concat(validate22.errors);
        errors = vErrors.length;
      }
    }
    if (data.builds !== void 0) {
      let data4 = data.builds;
      if (Array.isArray(data4)) {
        if (data4.length > 64) {
          const err8 = { instancePath: instancePath + "/builds", schemaPath: "#/properties/builds/maxItems", keyword: "maxItems", params: { limit: 64 }, message: "must NOT have more than 64 items" };
          if (vErrors === null) {
            vErrors = [err8];
          } else {
            vErrors.push(err8);
          }
          errors++;
        }
        const len0 = data4.length;
        for (let i0 = 0; i0 < len0; i0++) {
          if (!validate44(data4[i0], { instancePath: instancePath + "/builds/" + i0, parentData: data4, parentDataProperty: i0, rootData })) {
            vErrors = vErrors === null ? validate44.errors : vErrors.concat(validate44.errors);
            errors = vErrors.length;
          }
        }
      } else {
        const err9 = { instancePath: instancePath + "/builds", schemaPath: "#/properties/builds/type", keyword: "type", params: { type: "array" }, message: "must be array" };
        if (vErrors === null) {
          vErrors = [err9];
        } else {
          vErrors.push(err9);
        }
        errors++;
      }
    }
  } else {
    const err10 = { instancePath, schemaPath: "#/type", keyword: "type", params: { type: "object" }, message: "must be object" };
    if (vErrors === null) {
      vErrors = [err10];
    } else {
      vErrors.push(err10);
    }
    errors++;
  }
  validate64.errors = vErrors;
  return errors === 0;
}
function validate63(data, { instancePath = "", parentData, parentDataProperty, rootData = data } = {}) {
  ;
  let vErrors = null;
  let errors = 0;
  if (!validate64(data, { instancePath, parentData, parentDataProperty, rootData })) {
    vErrors = vErrors === null ? validate64.errors : vErrors.concat(validate64.errors);
    errors = vErrors.length;
  }
  validate63.errors = vErrors;
  return errors === 0;
}
export {
  buildShape,
  historyShape,
  inputShape,
  jobShape,
  requestBuildShape,
  savedRunShape
};
