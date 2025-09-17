// export default function longestCommonSubsequence(
//   str1: string,
//   str2: string,
// ): number {
//   let len1 = str1.length;
//   let len2 = str2.length;

//   // create the grid
//   let grid: number[][] = Array.from({ length: len1 + 1 }, () =>
//     Array(len2 + 1).fill(0),
//   );

//   for (let col = len1 - 1; col >= 0; col--) {
//     for (let row = len2 - 1; row >= 0; row--) {
//       if (str1[col] === str2[row]) {
//         grid[col][row] = 1 + grid[col + 1][row + 1];
//       } else {
//         grid[col][row] = Math.max(grid[col + 1][row], grid[col][row + 1]);
//       }
//     }
//   }
//   return grid[0][0];
// }
export default function longestCommonSubsequence(
  str1: string,
  str2: string,
): number {
  let curr: number[] = Array(str2.length + 1).fill(0);
  let next: number[] = Array(str2.length + 1).fill(0);

  for (let row = str1.length - 1; row >= 0; row--) {
    [curr, next] = [next, curr];
    for (let col = str2.length - 1; col >= 0; col--) {
      if (str1[row] === str2[col]) {
        curr[col] = 1 + next[col + 1];
      } else {
        curr[col] = Math.max(next[col], curr[col + 1]);
      }
    }
  }
  return curr[0];
}
