// stimuli_list.js
// 실험에 사용될 모든 음원 파일명과 메타데이터를 정의합니다.

// ==========================================
// 1단계 & 2단계용 파일 리스트 (Folder: EMO_PRACT_rvb)
// ==========================================

// 1단계: Discrimination (총 4쌍)
const PAIRS_DISCRIMINATION = [
    // Sad vs Fear (F/M) - Utterance 137
    { 
        t: "sad", 
        a: "sad_F137.wav", 
        b: "fear_F137.wav" 
    },
    { 
        t: "sad", 
        a: "sad_M137.wav", 
        b: "fear_M137.wav" 
    },
    // Amu vs Rel (F/M) - Utterance 545
    { 
        t: "amu", 
        a: "amu_F545.wav", 
        b: "rel_F545.wav" 
    },
    { 
        t: "amu", 
        a: "amu_M545.wav", 
        b: "rel_M545.wav" 
    }
];

// 2단계: Dry vs Rvb (총 8개 타겟)
// 실제 파일은 로직에서 _rvb 접미사를 붙여서 생성합니다.
const TARGETS_DRY_RVB = [
    { emo: "sad",  sex: "F", utt: "137" },
    { emo: "sad",  sex: "M", utt: "137" },
    { emo: "fear", sex: "F", utt: "137" },
    { emo: "fear", sex: "M", utt: "137" },
    { emo: "amu",  sex: "F", utt: "545" },
    { emo: "amu",  sex: "M", utt: "545" },
    { emo: "rel",  sex: "F", utt: "545" },
    { emo: "rel",  sex: "M", utt: "545" }
];


// ==========================================
// 3단계용 파일 리스트 (Folder: EMO_137)
// ==========================================
// 5 Emotions * 2 Sex = 10 Files
const FILES_PRACTICE_5AFC = [
    "amu_F137.wav", "amu_M137.wav",
    "ang_F137.wav", "ang_M137.wav",
    "sad_F137.wav", "sad_M137.wav",
    "fear_F137.wav", "fear_M137.wav",
    "surp_F137.wav", "surp_M137.wav"
];


// ==========================================
// 4단계용 파일 리스트 (Folder: EMO_STIM_rvb)
// ==========================================
// 5 Emos * 2 Sex * 2 Utterances * 3 Conditions (Dry, Rvb1, Rvb2) = 60 Files
// Utterance 번호가 137과 545라고 가정했습니다. (다르면 이 배열을 직접 수정하세요)
const FILES_TEST_5AFC = [];

const emotions = ["amu", "ang", "sad", "fear", "surp"];
const sexes = ["F", "M"];
const utterances = ["820", "545"]; // 만약 다른 번호를 쓴다면 여기를 수정하세요
const conditions = ["", "_rvb1", "_rvb2"]; // 빈 문자열은 dry를 의미 (예: amu_F137.wav)

emotions.forEach(emo => {
    sexes.forEach(sex => {
        utterances.forEach(utt => {
            conditions.forEach(cond => {
                // 파일명 생성 예: amu_F137.wav 또는 amu_F137_rvb1.wav
                const filename = `${emo}_${sex}${utt}${cond}.wav`;
                FILES_TEST_5AFC.push(filename);
            });
        });
    });
});
// stimuli_list.js 맨 아래에 추가해서 확인용으로 사용
console.log("Stage 4 파일 목록:", FILES_TEST_5AFC);
